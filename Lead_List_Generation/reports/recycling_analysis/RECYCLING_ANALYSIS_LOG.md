# Lead Recycling Optimization Analysis
**Started**: December 24, 2025
**Objective**: Determine optimal re-engagement timing to boost conversion to 5-6%

## Key Hypothesis
Leads we contacted but didn't close may have moved firms AFTER we contacted them.
By re-engaging at the optimal time, we can significantly boost conversion rates.

## Analysis Progress

### Phase 0: Setup
- [x] Created directory structure
- [x] Initialized analysis log

### Phase 1: Identify Closed/Lost with Firm Changes
- [x] Queried leads with subsequent firm changes
- [x] Analyzed outcome by move timing
- **Key Finding**: 2,270 leads (6.3%) moved after contact; 91-180 days window has 8.52% conversion (2.63x lift)

### Phase 2: Optimal Re-engagement Timing
- [x] Ran timing analysis
- [x] Identified optimal window: 91-180 days after contact
- **Key Finding**: Best conversion at 91-180 days (8.52%), secondary peaks at 31-60 days (6.02%) and 61-90 days (6.64%)

### Phase 3: Current Recyclable Pool
- [x] Queried current recyclable leads
- [x] Calculated pool by priority tier
- **Key Finding**: 26,311 recyclable leads available, weighted 3.7% conversion rate

### Phase 4: Hybrid Optimization
- [x] Analyzed hybrid scenarios
- [x] Compared 70/30, 60/40, and optimized allocations
- **Key Finding**: 70/30 split achieves 3.9% conversion (vs 3.2% baseline)

### Phase 5: Final Report
- [x] Generated SGA_Optimization_Version2.md
- **Report Location**: `reports/SGA_Optimization_Version2.md`

### Phase 6: Implementation SQL
- [ ] Created hybrid_lead_list_generator.sql

