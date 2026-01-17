# Lovable Dashboard Templates

## 🎨 How to Build Dashboards with Lovable

Visit [lovable.dev](https://lovable.dev) and use these prompts to build your dashboards in 1-2 hours.

---

## Dashboard 1: Doctor Portal

### Lovable Prompt:

```
Create a healthcare doctor portal dashboard with a modern, clean design:

LAYOUT:
- Top navigation bar with "CarePoint AI" logo and doctor profile
- Main area with 3 columns

COLUMN 1 - Active Consultations (60% width):
- Title: "Live Consultations"
- Display consultation cards in a scrollable list
- Each card shows:
  - Patient ID (top left)
  - Timestamp (top right)
  - Location/Station badge
  - Query text preview (2 lines max)
  - Urgency badge (color-coded: green=LOW, yellow=MEDIUM, orange=HIGH, red=EMERGENCY)
  - Confidence meter (0-100%)
  - "View Details" button
  - "Join Video Call" button (prominent, blue)

COLUMN 2 - Council Breakdown (20% width):
- Title: "AI Council Votes"
- Pie chart showing:
  - Unanimous decisions
  - Majority decisions
  - Split decisions
- Legend with percentages

COLUMN 3 - Model Performance (20% width):
- Title: "Model Confidence"
- Three progress bars:
  - GPT-4o (blue)
  - Claude Sonnet 4 (purple)
  - Gemini 2.0 (orange)
- Show average confidence per model

BOTTOM SECTION - Patient Queue:
- Horizontal scrollable list
- Small patient cards waiting for review
- Shows patient ID, urgency, waiting time

STYLING:
- Use healthcare-friendly colors (blues, greens, clean white)
- Urgency badges: green (#10B981), yellow (#F59E0B), orange (#F97316), red (#EF4444)
- Rounded corners, subtle shadows
- Responsive design

DATA INTEGRATION:
- Fetch from: https://api.arize.com/v1/spaces/{SPACE_ID}/traces
- Poll every 5 seconds for updates
- Add Authorization header with Arize API key
```

### Arize API Integration Code:

```javascript
// Add this to your Lovable project
const ARIZE_API_KEY = "your_arize_api_key";
const SPACE_ID = "your_space_id";

async function fetchConsultations() {
  const response = await fetch(
    `https://api.arize.com/v1/spaces/${SPACE_ID}/traces`,
    {
      headers: {
        Authorization: `Bearer ${ARIZE_API_KEY}`,
        "Content-Type": "application/json",
      },
    }
  );

  const data = await response.json();

  // Transform traces into consultation cards
  return data.traces.map((trace) => ({
    patientId: trace.attributes["patient_id"],
    location: trace.attributes["location"],
    query: trace.attributes["input_text"],
    urgency: trace.attributes["urgency"],
    confidence: trace.attributes["confidence"],
    timestamp: trace.start_time,
    councilVotes: trace.attributes["council_votes"],
  }));
}

// Poll for updates
setInterval(fetchConsultations, 5000);
```

---

## Dashboard 2: Admin Analytics

### Lovable Prompt:

```
Create a healthcare analytics dashboard for administrators with data visualizations:

HEADER:
- Title: "CarePoint AI Analytics"
- Date range selector
- Refresh button

TOP ROW - Key Metrics (4 cards):
1. Total Consultations Today
   - Large number
   - Trend indicator (↑ 12%)
   - Icon: medical clipboard

2. Emergency Detection Rate
   - Percentage
   - Color-coded (red if high)
   - Icon: alert symbol

3. Average Response Time
   - Seconds
   - Target line at 3s
   - Icon: clock

4. Council Agreement Rate
   - Percentage
   - Icon: checkmark circle

MIDDLE SECTION - Charts (2 columns):

LEFT COLUMN:
- "Model Performance Comparison" (Bar Chart)
  - X-axis: GPT-4o, Claude, Gemini
  - Y-axis: Accuracy score
  - Show average confidence per model
  - Color-coded bars

RIGHT COLUMN:
- "Response Time Trend" (Line Chart)
  - X-axis: Time (24 hours)
  - Y-axis: Response time (seconds)
  - Three lines: Fast Path, Visual Path, Council Path
  - Different colors for each path

BOTTOM SECTION - Additional Insights (2 columns):

LEFT:
- "Council Decision Distribution" (Pie Chart)
  - Unanimous (green)
  - Majority (blue)
  - Split (orange)
  - With percentages

RIGHT:
- "Device Status Map" (Grid)
  - Show all first aid stations
  - Color-coded by status:
    - Green: Online
    - Yellow: Warning
    - Red: Offline
  - Click for details

STYLING:
- Professional admin theme (dark mode optional)
- Use charts library (Chart.js or Recharts)
- Smooth animations
- Mobile responsive

DATA INTEGRATION:
- Fetch metrics from: https://api.arize.com/v1/spaces/{SPACE_ID}/metrics
- Update every 30 seconds
```

### Arize API Integration Code:

```javascript
async function fetchMetrics() {
  const response = await fetch(
    `https://api.arize.com/v1/spaces/${SPACE_ID}/metrics`,
    {
      headers: {
        Authorization: `Bearer ${ARIZE_API_KEY}`,
      },
    }
  );

  const data = await response.json();

  return {
    totalConsultations: data.total_spans,
    emergencyRate: calculateEmergencyRate(data),
    avgResponseTime: data.avg_latency_ms / 1000,
    councilAgreement: calculateAgreementRate(data),
    modelPerformance: {
      gpt4: data.model_metrics["gpt-4o"],
      claude: data.model_metrics["claude-sonnet-4"],
      gemini: data.model_metrics["gemini-2.0-flash"],
    },
  };
}

function calculateEmergencyRate(data) {
  const emergencies = data.traces.filter(
    (t) => t.attributes["urgency"] === "EMERGENCY"
  ).length;
  return (emergencies / data.total_spans) * 100;
}

function calculateAgreementRate(data) {
  const unanimous = data.traces.filter((t) => {
    const votes = t.attributes["council_votes"];
    return Object.values(votes).every((v) => v.urgency === votes[0].urgency);
  }).length;
  return (unanimous / data.total_spans) * 100;
}
```

---

## 🚀 Deployment Steps

1. **Build on Lovable**:

   - Sign in to lovable.dev
   - Create new project
   - Paste the prompt
   - Let Lovable generate the UI

2. **Add Arize Integration**:

   - Copy the API integration code
   - Paste into your Lovable project
   - Update SPACE_ID and API_KEY

3. **Test**:

   - Run your CarePoint API locally
   - Generate some test consultations
   - Watch them appear in dashboard

4. **Deploy**:

   - Lovable auto-deploys to Vercel
   - Get shareable URL
   - Share with team

5. **Optional - LiveKit Video**:
   - Add LiveKit React components
   - Generate room tokens from backend
   - Enable video consultations

---

## 📊 Arize API Endpoints Reference

### Get Recent Traces

```
GET https://api.arize.com/v1/spaces/{space_id}/traces
Query Params: limit, start_time, end_time
```

### Get Metrics

```
GET https://api.arize.com/v1/spaces/{space_id}/metrics
Query Params: metric_type, aggregation, time_range
```

### Get Model Performance

```
GET https://api.arize.com/v1/spaces/{space_id}/models/{model_name}/metrics
```

### Authentication

```
Authorization: Bearer YOUR_API_KEY
```

---

## 💡 Tips for Lovable Development

1. **Iterate**: Start with basic layout, then add features
2. **Mock Data**: Use mock data initially, then connect to Arize
3. **Components**: Break into reusable components
4. **Real-time**: Use WebSockets or polling for live updates
5. **Error Handling**: Add loading states and error messages
6. **Responsive**: Test on mobile, tablet, desktop
7. **Accessibility**: Add ARIA labels for screen readers

---

## 🎯 Demo Script

When demoing to stakeholders:

1. **Show API**: Run `python test_api.py`
2. **Show Traces**: Open Arize platform, show real-time traces
3. **Show Dashboard**: Open Lovable dashboard, show live updates
4. **Demo Flow**: Submit emergency query → Show council debate → Show final response
5. **Analytics**: Show performance metrics and trends

---

Built with ❤️ using Lovable, Arize, and LangGraph
