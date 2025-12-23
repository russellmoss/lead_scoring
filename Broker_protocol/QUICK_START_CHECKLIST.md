# Broker Protocol Automation - Quick Start Checklist

**Print this and check off each item as you complete it!**

---

## ☐ WEEK 1: Setup & Initial Load

### Day 1: Environment Prep (30 min)
- [ ] Install Python dependencies:
  ```bash
  pip install -r requirements.txt --break-system-packages
  ```
- [ ] Verify BigQuery access to `FinTrx_data_CA` dataset
- [ ] Authenticate with Google Cloud:
  ```bash
  gcloud auth application-default login
  ```
- [ ] Update `config.py` with your settings

### Day 2: Let Cursor.ai Build Everything (1-2 hours)
- [ ] Open Cursor.ai with BigQuery MCP connection
- [ ] Give it `CURSOR_AI_DEVELOPMENT_GUIDE.md`
- [ ] Let it run through all 6 phases
- [ ] Verify in console: All tables created
- [ ] Verify in console: All Python scripts created
- [ ] Verify in console: Initial data loaded

### Day 3: Validate Initial Data (30 min)
- [ ] Check total firms loaded (expect ~2,500-3,000)
- [ ] Check match rate (expect >70%)
- [ ] Review sample of matched firms
- [ ] Review sample of unmatched firms
- [ ] Run validation queries from guide

### Day 4-5: First Manual Review (1-2 hours)
- [ ] Export top 50 unmatched firms (by AUM)
- [ ] Search FINTRX manually for matches
- [ ] Add manual matches to BigQuery
- [ ] Flag remaining as "reviewed - not in FINTRX"
- [ ] Document any systematic issues

---

## ☐ WEEK 2: Automation Setup

### Setup n8n Workflow (2-3 hours)
- [ ] Install required n8n nodes
- [ ] Create Google Cloud service account
- [ ] Configure credentials in n8n
- [ ] Build 12-node workflow (follow N8N_SETUP_GUIDE.md)
- [ ] Test workflow manually
- [ ] Verify data loads to BigQuery
- [ ] Test error alerts
- [ ] Enable schedule (1st & 15th at 9 AM ET)

### First Automated Run
- [ ] Wait for next scheduled run OR trigger manually
- [ ] Check email for success notification
- [ ] Verify data updated in BigQuery
- [ ] Check scrape log for any issues
- [ ] Review any new unmatched firms

---

## ☐ WEEK 3-4: Integration

### Lead Scoring Integration
- [ ] Add broker protocol features to ML pipeline:
  - [ ] `is_broker_protocol_firm` (binary)
  - [ ] `broker_protocol_tenure_years` (continuous)
  - [ ] `broker_protocol_recently_withdrawn` (binary, negative)
- [ ] Test features on sample leads
- [ ] Backtest model performance
- [ ] Deploy to production pipeline

### Salesforce Integration (Optional)
- [ ] Create broker protocol custom fields
- [ ] Set up data sync from BigQuery
- [ ] Update lead views/reports
- [ ] Train sales team on new data

---

## ☐ ONGOING: Maintenance

### Weekly (10 minutes)
- [ ] Check last scrape status
- [ ] Review top 10 unmatched firms
- [ ] Add manual matches if needed

### Monthly (30 minutes)
- [ ] Check match rate trend
- [ ] Review all high-AUM unmatched firms
- [ ] Update matching rules if needed
- [ ] Validate data quality metrics

### Quarterly (1 hour)
- [ ] Full system review
- [ ] Measure impact on lead quality
- [ ] Document ROI
- [ ] Plan improvements

---

## 📊 Success Metrics

### Week 1 Targets
- [ ] Match rate: **>70%**
- [ ] Data loaded: **YES**
- [ ] Validation passed: **YES**

### Month 1 Targets
- [ ] Automated runs: **2+ successful**
- [ ] Match rate: **>75%**
- [ ] Manual review: **<15% need review**

### Month 3 Targets
- [ ] Automated runs: **6+ successful**
- [ ] Match rate: **>80%**
- [ ] Manual review: **<10% need review**
- [ ] Lead scoring: **Integrated**

### Month 6 Targets
- [ ] Match rate: **>85%**
- [ ] Manual review: **<5% need review**
- [ ] ROI: **Documented**
- [ ] Team: **Fully trained**

---

## 🚨 Red Flags (Stop and Fix)

- [ ] Match rate drops below 60%
- [ ] Automated run fails 2+ times in a row
- [ ] BigQuery errors
- [ ] Excel file structure changed
- [ ] More than 30% need manual review

**If you see any red flags**: Check troubleshooting section in main guides!

---

## 📞 Key Resources

- **Development Guide**: `CURSOR_AI_DEVELOPMENT_GUIDE.md`
- **n8n Setup**: `N8N_SETUP_GUIDE.md`
- **Configuration**: `config.py`
- **Python Deps**: `requirements.txt`

---

## ✅ Completion Checklist

- [ ] All BigQuery tables exist
- [ ] Initial data loaded (>2,500 firms)
- [ ] Match rate >70%
- [ ] n8n workflow running
- [ ] First automated run successful
- [ ] Manual review process documented
- [ ] Team trained on new data
- [ ] Lead scoring integration complete

**Status**: ⬜ Not Started | 🟡 In Progress | ✅ Complete

---

**Last Updated**: December 22, 2024
**Estimated Total Time**: 10-15 hours (spread over 3-4 weeks)
