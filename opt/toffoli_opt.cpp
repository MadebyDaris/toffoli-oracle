/* toffoli-opt: AND-count (multiplicative complexity) optimization of an XAG with mockturtle.
 *
 *   toffoli-opt in.v out.v [--rounds N]
 *
 * Reads XAG Verilog, runs the MC flow explored in sandbox/mockturtle/mc_flow.cpp, checks the result
 * against the input with a SAT miter, writes Verilog and prints one JSON line of statistics.
 * Later: depth passes and cut tracing into an e-graph (see README, "The pass, step by step").
 */

#include <cstdint>
#include <cstdlib>
#include <string>

#include <fmt/format.h>
#include <lorina/verilog.hpp>

#include <mockturtle/algorithms/cleanup.hpp>
#include <mockturtle/algorithms/cut_rewriting.hpp>
#include <mockturtle/algorithms/equivalence_checking.hpp>
#include <mockturtle/algorithms/miter.hpp>
#include <mockturtle/algorithms/node_resynthesis/xag_minmc2.hpp>
#include <mockturtle/algorithms/xag_optimization.hpp>
#include <mockturtle/io/verilog_reader.hpp>
#include <mockturtle/io/write_verilog.hpp>
#include <mockturtle/networks/xag.hpp>
#include <mockturtle/properties/mccost.hpp>

using namespace mockturtle;

namespace
{

std::string stats_json( xag_network const& xag )
{
  uint32_t ands = 0, xors = 0;
  xag.foreach_gate( [&]( auto const& n ) { ( xag.is_and( n ) ? ands : xors )++; } );
  return fmt::format( R"({{"ands": {}, "xors": {}, "and_depth": {}}})", ands, xors, multiplicative_complexity_depth( xag ).value_or( 0 ) );
}

xag_network optimize_mc( xag_network xag, uint32_t max_rounds )
{
  xag = xag_constant_fanin_optimization( xag );
  xag = xag_dont_cares_optimization( xag );

  future::xag_minmc_resynthesis resyn;
  cut_rewriting_params ps;
  ps.cut_enumeration_ps.cut_size = 5u; /* the built-in min-MC database covers up to 5 inputs */
  ps.min_cand_cut_size = 2u;           /* default 3 misses (~a & ~b) ^ (a & b) = XNOR(a, b) */
  for ( auto round = 0u; round < max_rounds; ++round )
  {
    const auto before = *multiplicative_complexity( xag );
    cut_rewriting_with_compatibility_graph( xag, resyn, ps, nullptr, mc_cost<xag_network>() );
    xag = cleanup_dangling( xag );
    if ( *multiplicative_complexity( xag ) >= before )
      break;
  }
  return xag;
}

} // namespace

int main( int argc, char** argv )
{
  if ( argc < 3 )
  {
    fmt::print( stderr, "usage: {} in.v out.v [--rounds N]\n", argv[0] );
    return 2;
  }
  uint32_t rounds = 10u;
  if ( argc >= 5 && std::string( argv[3] ) == "--rounds" )
    rounds = static_cast<uint32_t>( std::strtoul( argv[4], nullptr, 10 ) );

  xag_network original;
  if ( lorina::read_verilog( argv[1], verilog_reader( original ) ) != lorina::return_code::success )
  {
    fmt::print( stderr, "[e] could not read {}\n", argv[1] );
    return 1;
  }

  const auto optimized = optimize_mc( original, rounds );

  const auto eq = equivalence_checking( *miter<xag_network>( original, optimized ) );
  if ( !eq || !*eq )
  {
    fmt::print( stderr, "[e] optimized network is {} to the input\n", eq ? "NOT equivalent" : "not provably equivalent" );
    return 1;
  }

  write_verilog( optimized, argv[2] );
  fmt::print( R"({{"input": "{}", "before": {}, "after": {}, "equivalent": true}})"
              "\n",
              argv[1], stats_json( original ), stats_json( optimized ) );
  return 0;
}
