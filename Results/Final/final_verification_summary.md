# Final verification summary

| Category | Passed | Total |
| --- | --- | --- |
| Fresh essential XSim | 13 | 13 |
| Fresh production equivalence/activity | 5 | 5 |
| Fresh original/production-scan functional activity | 1 | 1 |
| Fresh representative original-universe fault | 1 | 1 |
| Fresh native WDB/WCFG pairs reopened | 6 | 6 |
| Archived processor experiments independently rechecked | 204 | 204 |
| Archived waveform figures rechecked against VCD | 45 | 45 |
| Earlier files unchanged by SHA-256 | 2486 | 2486 |

Counts above are read from actual result files. Archived campaign checks compare all 256 captures, every prefix signature, routing configuration, sequence counts, isolation evidence and measured activity against independent models. Fresh native case CSVs and logs are under Verification/Essential and Verification/Activity. The original intentional WAIT breakpoint assertion is accepted only with the exact PC, differential state and expected output sequence. Simulated time is bounded below 100 ms; the longest archived processor run is 661.6002 us.

The FPGA timing report is separate: a passing behavioral simulation does not establish timing closure. No historical result is overwritten.
