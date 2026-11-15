/* caterpillar's mapping strategies on the XAGs.
 *
 * For each strategy we compare
 *   reported T  : caterpillar's own count (detail::qc_stats). It charges 4 T
 * for a Toffoli onto a clean target and 0 T when the same target is hit again
 * (assumes measurement-based uncomputation). emitted CCX : the Toffolis
 * actually present in the netlist it hands you. On a machine that pays per
 * Toffoli, emitted CCX is the real bill; reported T / 4 is what you were told.
 *
 * Built against caterpillar's own bundled (2020) mockturtle and tweedledum, not
 * third_party/mockturtle.
 */

#include <cstdint>
#include <filesystem>
#include <string>
#include <vector>

#include <fmt/format.h>
#include <kitty/dynamic_truth_table.hpp>
#include <lorina/verilog.hpp>
#include <mockturtle/algorithms/simulation.hpp>
#include <mockturtle/io/verilog_reader.hpp>
#include <mockturtle/networks/xag.hpp>
#include <tweedledum/networks/netlist.hpp>

#include <caterpillar/details/utils.hpp>
#include <caterpillar/structures/stg_gate.hpp>
#include <caterpillar/synthesis/lhrs.hpp>
#include <caterpillar/synthesis/strategies/bennett_mapping_strategy.hpp>
#include <caterpillar/synthesis/strategies/eager_mapping_strategy.hpp>
#include <caterpillar/synthesis/strategies/xag_mapping_strategy.hpp>
#include <caterpillar/verification/circuit_to_logic_network.hpp>

using namespace caterpillar;
using namespace mockturtle;
using circuit_t = tweedledum::netlist<stg_gate>;

namespace {

uint32_t count_ands(xag_network const &xag) {
  uint32_t n = 0;
  xag.foreach_gate([&](auto const &g) { n += xag.is_and(g) ? 1 : 0; });
  return n;
}

std::string classical_check(xag_network const &xag, circuit_t const &qnet,
                            logic_network_synthesis_stats const &st) {
  if (xag.num_pis() > 16)
    return "skipped";
  const auto back =
      circuit_to_logic_network<xag_network>(qnet, st.i_indexes, st.o_indexes);
  if (!back)
    return "not convertible";
  default_simulator<kitty::dynamic_truth_table> sim(xag.num_pis());
  return simulate<kitty::dynamic_truth_table>(xag, sim) ==
                 simulate<kitty::dynamic_truth_table>(*back, sim)
             ? "ok"
             : "MISMATCH";
}

void run(std::string const &label, xag_network const &xag,
         mapping_strategy<xag_network> &strategy, bool low_tdepth) {
  circuit_t qnet;
  logic_network_synthesis_stats st;
  if (!logic_network_synthesis(qnet, xag, strategy, {}, {}, &st)) {
    fmt::print("    {:<24} failed\n", label);
    return;
  }

  uint32_t ccx = 0, mcx = 0;
  qnet.foreach_cgate([&](auto const &g) {
    const auto c = g.gate.num_controls();
    ccx += c == 2 ? 1 : 0;
    mcx += c > 2 ? 1 : 0;
  });
  const auto [cnot, t_count, t_depth] =
      caterpillar::detail::qc_stats(qnet, low_tdepth);

  fmt::print("    {:<24} reported T={:>5} (= {:>4} Tof)  T-depth={:>4}   "
             "emitted CCX={:>5}{}  qubits={:>4}  check={}\n",
             label, t_count, t_count / 4, t_depth, ccx,
             mcx ? fmt::format(" (+{} MCX>2)", mcx) : "", qnet.num_qubits(),
             classical_check(xag, qnet, st));
}

} // namespace

int main(int argc, char **argv) {
  const std::filesystem::path bench = argc > 1 ? argv[1] : "bench/xag";
  std::vector<std::filesystem::path> files;
  for (auto const &e : std::filesystem::directory_iterator(bench))
    if (e.path().extension() == ".v")
      files.push_back(e.path());
  std::sort(files.begin(), files.end());

  for (auto const &path : files) {
    xag_network xag;
    if (lorina::read_verilog(path.string(), verilog_reader(xag)) !=
        lorina::return_code::success) {
      fmt::print("[e] could not read {}\n", path.string());
      continue;
    }
    fmt::print("\n== {} ==  {} ANDs, {} inputs\n", path.stem().string(),
               count_ands(xag), xag.num_pis());

    bennett_mapping_strategy<xag_network> bennett;
    run("bennett", xag, bennett, false);
    eager_mapping_strategy<xag_network> eager;
    run("eager", xag, eager, false);
    xag_mapping_strategy lowt;
    run("xag low-T", xag, lowt, false);
    xag_fast_lowt_mapping_strategy fast;
    run("xag low-T (fast)", xag, fast, false);
    xag_low_depth_mapping_strategy lowd;
    run("xag low-depth", xag, lowd, true);
  }
  return 0;
}
