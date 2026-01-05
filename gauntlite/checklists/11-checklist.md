### HUMAN SIGN-OFF CHECKLIST
(Implementation Agent must copy this verbatim at the end of its Phase 11 patch)

[ ] Setting `OPEN_SOURCE_ONLY=true` routes all agent calls through local models  
[ ] Local inference stack spins up via single command documented in README  
[ ] Prompts adapt context length and temperature for open-source models without manual edits  
[ ] CI matrix runs proprietary and eco mode smoke tests  
[ ] BudgetGuard reports $0 incremental spend while tracking energy/time cost  
[ ] Performance benchmarks captured comparing both modes (tokens/sec, latency)  
[ ] Streamlit UI indicates active mode and warns about capability differences  
[ ] Documentation lists supported models, hardware specs, and fallbacks  
[ ] Regression tests confirm parity within defined tolerances  
[ ] Design Ledger records decision and constraints for eco mode
