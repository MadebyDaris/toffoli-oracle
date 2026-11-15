/* mockturtle's multiplicative-complexity (MC)
 *
 * For each benchmark we build a deliberately naive AIG, convert it to an XAG,
 * then apply the MC passes one at a time and print what each pass changed.
 * The final XAG is SAT-checked against the original and written as Verilog
 * so the Python side (toffoli_oracle.xag) can read it.
 *
 *   AND count       -> Toffoli count (with measurement-based uncomputation)
 *   AND depth (MD)  -> Toffoli depth
 *   XOR count       -> CNOT count (Clifford, ~free on a fault-tolerant machine)
 */

#include <cstdint>
#include <filesystem>
#include <functional>
#include <string>
#include <vector>

#include <fmt/format.h>

#include <mockturtle/algorithms/cleanup.hpp>
#include <mockturtle/algorithms/cut_rewriting.hpp>
#include <mockturtle/algorithms/equivalence_checking.hpp>
#include <mockturtle/algorithms/miter.hpp>
#include <mockturtle/algorithms/node_resynthesis/xag_minmc2.hpp>
#include <mockturtle/algorithms/xag_optimization.hpp>
#include <mockturtle/generators/arithmetic.hpp>
#include <mockturtle/io/write_verilog.hpp>
#include <mockturtle/networks/aig.hpp>
#include <mockturtle/networks/xag.hpp>
#include <mockturtle/properties/mccost.hpp>

using namespace mockturtle;
namespace
{

struct xag_stats
{
  uint32_t gates{}, ands{}, xors{}, and_depth{};
};

xag_stats stats_of( xag_network const& xag )
{
  xag_stats s;
  s.gates = xag.num_gates();
  xag.foreach_gate( [&]( auto const& n ) {
    if ( xag.is_and( n ) )
      ++s.ands;
    else
      ++s.xors;
  } );
  s.and_depth = multiplicative_complexity_depth( xag ).value_or( 0 );
  return s;
}

void print_row( std::string const& step, xag_network const& xag )
{
  const auto s = stats_of( xag );
  fmt::print( "  {:<34} gates={:>5}  AND={:>5}  XOR={:>5}  AND-depth={:>4}\n", step, s.gates, s.ands, s.xors, s.and_depth );
}

/* benchmark generators (naive on purpose: AIG-style, no XOR gates) */

template<class Ntk = aig_network> Ntk make_adder( uint32_t n )
{
  Ntk aig;
  /*adder a and b of size n*/
  std::vector<typename Ntk::signal> a( n ), b( n );
  std::generate( a.begin(), a.end(), [&] { return aig.create_pi(); } );
  std::generate( b.begin(), b.end(), [&] { return aig.create_pi(); } );
  auto carry = aig.get_constant( false );
  carry_ripple_adder_inplace( aig, a, b, carry );
  for ( auto const& s : a )
    aig.create_po( s );
  aig.create_po( carry );
  return aig;
}

aig_network make_multiplier( uint32_t n )
{
  aig_network aig;
  std::vector<aig_network::signal> a( n ), b( n );
  std::generate( a.begin(), a.end(), [&] { return aig.create_pi(); } );
  std::generate( b.begin(), b.end(), [&] { return aig.create_pi(); } );
  for ( auto const& p : carry_ripple_multiplier( aig, a, b ) )
    aig.create_po( p );
  return aig;
}

/* a < b (unsigned): the borrow out of a - b */
aig_network make_less_than( uint32_t n )
{
  aig_network aig;
  std::vector<aig_network::signal> a( n ), b( n );
  std::generate( a.begin(), a.end(), [&] { return aig.create_pi(); } );
  std::generate( b.begin(), b.end(), [&] { return aig.create_pi(); } );
  auto carry = aig.get_constant( true ); /* a + ~b + 1 */
  carry_ripple_subtractor_inplace( aig, a, b, carry );
  aig.create_po( !carry );
  return aig;
}

/* the flow */
xag_network minmc_rewrite( xag_network xag )
{
  future::xag_minmc_resynthesis resyn; /* built-in DB of MC-optimum XAGs up to 5 inputs */
  cut_rewriting_params ps;
  ps.cut_enumeration_ps.cut_size = 5u;
  ps.min_cand_cut_size = 2u; /* default 3 skips 2-input cuts, e.g. (~a & ~b) ^ (a & b) = XNOR(a, b) costs 2 ANDs */
  cut_rewriting_with_compatibility_graph( xag, resyn, ps, nullptr, mc_cost<xag_network>() );
  return cleanup_dangling( xag );
}


/* pipeline function for aig/xag with optimization phase */
void run( std::string const& name, aig_network const& aig, std::filesystem::path const& out_dir )
{
  fmt::print( "\n== {} ==  ({} inputs, {} outputs)\n", name, aig.num_pis(), aig.num_pos() );

  const auto original = cleanup_dangling<aig_network, xag_network>( aig );
  print_row( "AIG -> XAG (naive)", original );

  auto xag = xag_constant_fanin_optimization( original );
  print_row( "xag_constant_fanin_optimization", xag );

  xag = xag_dont_cares_optimization( xag );
  print_row( "xag_dont_cares_optimization", xag );

  for ( auto it = 1u; it <= 10u; ++it )
  {
    const auto before = *multiplicative_complexity( xag );
    xag = minmc_rewrite( xag );
    print_row( fmt::format( "cut_rewriting(minmc) #{}", it ), xag );
    if ( *multiplicative_complexity( xag ) >= before )
      break;
  }

  const auto m = *miter<xag_network>( original, xag );
  const auto eq = equivalence_checking( m );
  fmt::print( "  equivalent to original (SAT miter): {}\n", eq ? ( *eq ? "yes" : "NO" ) : "unknown" );

  const auto path = out_dir / ( name + ".v" );
  write_verilog( xag, path.string() );
  std::filesystem::create_directories( out_dir / "naive" ); /* unoptimized input, e.g. for opt/toffoli-opt */
  write_verilog( original, ( out_dir / "naive" / ( name + ".v" ) ).string() );
  fmt::print( "  wrote {}\n", path.string() );
}

} // namespace

int main( int argc, char** argv )
{
  const std::filesystem::path out_dir = argc > 1 ? argv[1] : "out";
  std::filesystem::create_directories( out_dir );

  run( "adder_4", make_adder( 4 ), out_dir );
  run( "adder_16", make_adder( 16 ), out_dir );

  /* same adder, but generated directly as an XAG: full_adder uses create_maj (1 AND) + create_xor3 */
  fmt::print( "\n== adder_16, generated natively as XAG (no optimization) ==\n" );
  print_row( "carry_ripple_adder_inplace<xag>", make_adder<xag_network>( 16 ) );

  run( "less_than_8", make_less_than( 8 ), out_dir );
  run( "multiplier_4", make_multiplier( 4 ), out_dir );
  run( "multiplier_8", make_multiplier( 8 ), out_dir );
  return 0;
}
