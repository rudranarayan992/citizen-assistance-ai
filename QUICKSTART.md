# Quick Start Guide - Citizen Assistance AI v3.1

## 🚀 Start the System (2 Commands)

### Terminal 1: Backend (FastAPI)
```bash
cd "c:\Users\rudra\Desktop\citizen-assistance-ai\backend works\backend"
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### Terminal 2: Frontend (React)
```bash
cd "c:\Users\rudra\Desktop\citizen-assistance-ai\frontend"
npm run dev
```

### Access Points
- **Frontend**: http://localhost:5175
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

---

## ✨ Key New Features

### 1. **AI-Powered Caching** 🔄
- Same query = Same cached response (guaranteed consistency)
- Instant response (100ms vs 3-5s without cache)
- Automatically saves to `data/core/ai_cache.json`

### 2. **Statutory Reference Extraction** ⚖️
Automatically extracts legal references:
```
Input: "IT Act 66A, IPC 419"
Output: [
  { act: "IT Act", section: "66A", year: 2000 },
  { act: "IPC", section: "419", year: 1860 }
]
```

### 3. **Local Volunteer Directory** 👥
Matches volunteers by:
- **City**: User's location (case-insensitive)
- **Category**: Incident type (cyber_fraud, mobile_theft, etc.)

Example: Cyber fraud in Cuttack → Returns "Amit Kumar - Cybersecurity Volunteer"

### 4. **Web Search Integration** 🔍
- Combines SerpApi results + Gemini-generated sources
- Removes duplicates by URL
- Adds relevant government portals

### 5. **Complete 12-Section Response** 📋
Every report includes:
1. Situation Analysis
2. Immediate Actions + Emergency Contacts
3. Safety Guidance
4. Actions After Reaching Safety
5. Digital & Financial Protection
6. Nearby Help
7. Expected Police Actions (24h)
8. Expected Investigation (48h)
9. Legal Sections
10. **Statutory References** ⭐
11. Escalation Options
12. Offline Help Points
13. Official Resources
14. **Volunteer Support** ⭐
15. Web Sources
16. Police Complaint Draft

---

## 📝 Test Workflow

### Step 1: Fill the Form
```
Incident: "I received a fake UPI payment link through WhatsApp"
Location: "Cuttack, Odisha"
Date/Time: Today at 8:00 PM
Name: John Doe
Age: 30
Gender: Male
```

### Step 2: Review & Submit
- Check all details
- Click "Submit Report"

### Step 3: View Results
System automatically:
1. ✅ Detects as "cyber_fraud"
2. ✅ Checks cache (first time = miss)
3. ✅ Calls Gemini for missing guide sections
4. ✅ Extracts statutory references
5. ✅ Finds volunteers in Cuttack
6. ✅ Retrieves web resources
7. ✅ Saves to cache for next time
8. ✅ Returns 16 sections of guidance

---

## 🔧 Configuration

### Add More Volunteers
Edit `data/core/volunteers.json`:
```json
{
  "volunteers": [
    {
      "name": "Your Name",
      "category": "cyber_fraud",
      "city": "Your City",
      "role": "Your Role",
      "phone": "+91-9999-9999",
      "email": "your@email.com",
      "notes": "What you help with"
    }
  ]
}
```

### Clear Cache
```bash
# Delete the cache file (will auto-regenerate)
rm data/core/ai_cache.json

# Or manually reset it to empty
echo '{}' > data/core/ai_cache.json
```

### View Cache Contents
```bash
# See what queries have been cached
cat data/core/ai_cache.json | python -m json.tool
```

---

## 🧪 Test Scenarios

### Scenario 1: Cyber Fraud (First Query)
**Expected**: 
- ⏱️ Takes 3-5 seconds (Gemini call)
- 📊 All 16 sections populated
- 📍 Volunteers from Cuttack shown
- 🔗 5-6 web resources included
- ✅ Statutory references extracted

### Scenario 2: Same Query Again
**Expected**:
- ⏱️ Instant response (< 100ms)
- 📋 Identical output to Scenario 1
- 💾 Retrieved from cache

### Scenario 3: Different Incident Type
**Expected**:
- 🆕 New cache entry created
- 🤖 Different AI guidance
- 👤 Different volunteers matched

---

## 📊 Monitor Cache Growth

```bash
# Check cache file size
ls -lh data/core/ai_cache.json

# Count cached entries
cat data/core/ai_cache.json | python -c "import json, sys; print(f'Cached: {len(json.load(sys.stdin))} queries')"

# See cache keys
cat data/core/ai_cache.json | python -c "import json, sys; print('\n'.join(json.load(sys.stdin).keys()))"
```

---

## 🐛 Troubleshooting

### Backend Won't Start
```bash
# Check if port 8000 is in use
lsof -i :8000

# Use different port
uvicorn main:app --reload --port 8001
```

### Frontend Shows Blank Sections
```bash
# Check browser console (F12) for errors
# Common issue: API not responding
# Solution: Ensure backend is running on port 8000
```

### Volunteers Not Showing
- Check `data/core/volunteers.json` is valid JSON
- Verify city matches (case-insensitive)
- Ensure category matches incident type

### Cache Not Working
- Ensure `ai_cache.json` exists in `data/core/`
- Check file permissions (must be readable/writable)
- Delete and restart if corrupted

---

## 📈 Performance Tips

### For Production Deployment
1. **Use Python venv**: Isolate dependencies
2. **Run without --reload**: `uvicorn main:app --workers 4`
3. **Use Gunicorn**: Better than uvicorn for production
4. **Enable HTTPS**: Use nginx as reverse proxy
5. **Database Cache**: Replace JSON with PostgreSQL for scalability

### Monitor Metrics
- **Cache hit rate**: (cache hits) / (total requests)
- **Response time**: Track first-time vs cached
- **API usage**: Monitor Gemini and SerpApi calls

---

## 🔐 Security Reminders

⚠️ **API Keys**:
```bash
# Set environment variables (don't commit to git)
export GEMINI_API_KEY="your-key-here"
export SERPAPI_API_KEY="your-key-here"

# Verify keys are set
echo $GEMINI_API_KEY
echo $SERPAPI_API_KEY
```

⚠️ **Input Validation**:
- All user inputs are validated via Pydantic
- SQL injection not possible (no SQL used)
- XSS protection enabled via React escaping

⚠️ **Rate Limiting**:
- Consider adding rate limits for production
- Currently no throttling on API endpoints

---

## 📞 Support Resources

### API Documentation
Visit: http://localhost:8000/docs
- Interactive Swagger UI
- Try-it-out feature
- Request/response examples

### Error Logs
```bash
# Backend logs show in terminal
# Check for:
# - Gemini API errors
# - SerpApi failures
# - Cache write failures
# - Volunteer matching issues
```

### Data Files
```
data/core/
├── victim_help_guides.json       → Incident guides
├── incident_types.json           → Incident definitions
├── volunteers.json               → Volunteer directory
├── ai_cache.json                 → Auto-populated cache
├── ai_response_templates.json    → Gemini templates
└── ...other files...
```

---

## 🎯 Next Steps

1. ✅ Start backend and frontend
2. ✅ Test with sample incident
3. ✅ Check cache file for entries
4. ✅ Verify volunteer matching
5. ✅ Review statutory references
6. ✅ Test web source deduplication
7. ✅ Download complaint draft

---

## 📊 Example Cache Entry

After first query, `ai_cache.json` contains:
```json
{
  "a8f3e2b1c9d4e7f2a3b5c8d1e4f7a0b3c6d9e2f5": {
    "immediate_actions": [
      "Block your SIM card immediately",
      "Check your bank account for unauthorized transactions"
    ],
    "legal_support": {
      "sections": ["IT Act 66A", "IPC 419"]
    },
    "web_sources": [
      {
        "title": "Report Cyber Fraud - National Cybercrime Portal",
        "url": "https://cybercrime.gov.in",
        "snippet": "Official portal for reporting cyber crimes in India"
      }
    ]
  }
}
```

---

## ✅ Verification Checklist

- [ ] Backend running on port 8000
- [ ] Frontend running on port 5175
- [ ] Can access http://localhost:5175
- [ ] Can submit incident report
- [ ] All 16 sections appear in response
- [ ] Statutory references show (e.g., "IT Act 66A (2000)")
- [ ] Volunteers appear for matching city
- [ ] Web sources are deduplicated
- [ ] Cache file grows after queries
- [ ] Second identical query is instant

---

**Version**: 3.1 (Enhanced)
**Status**: ✅ Ready to Use
**Last Updated**: 2026-03-16

🚀 Happy Coding!
