# Final FPGA synthesis and implementation summary

| Configuration | LUT | FF | Latches | BRAM | DSP | Stage |
| --- | --- | --- | --- | --- | --- | --- |
| baseline | 5380 | 2035 | 0 | 1 | 7 | Routed |
| scan_enabled | 6360 | 3101 | 0 | 0 | 7 | Routed |
| full_lbist | 6511 | 3240 | 0 | 0 | 7 | Routed |

| Configuration | Stage | WNS (ns) | TNS (ns) | WHS (ns) | Closure |
| --- | --- | --- | --- | --- | --- |
| baseline | Routed | -77.054 | -5443.598 | -2.793 | FAIL |
| scan_enabled | Routed | -77.212 | -7334.359 | -2.728 | FAIL |
| full_lbist | Routed | -76.315 | -7796.277 | -2.726 | FAIL |

| Comparison | LUT overhead (%) | FF overhead (%) | Stage |
| --- | --- | --- | --- |
| Scan/isolation vs baseline | 18.2156 | 52.3833 | Routed |
| Complete LBIST vs baseline | 21.0223 | 59.2138 | Routed |
| LBIST addition vs scan/isolation | 2.3742 | 4.4824 | Routed |

Actual native report_utilization counts; same Artix-7 part, virtual processor boundary, MMCM and constraints. No fault mux/debug hardware. See FPGA_Analysis/README.md for assumptions, execution status and power limitations.
