# Study Pilot 📚 — AI-Powered Smart Study Planner

An intelligent, interactive study assistant that transforms raw syllabus PDF documents into optimized, high-yield weekly study schedules. The application automatically prioritizes topics based on exam proximity and subject weightages, exports beautiful PDF timetables, and sends automated daily reminder emails straight to your inbox.

---

## ✨ Key Features

- **AI-Powered Syllabus Parsing**: Upload any academic syllabus PDF; the integrated LLM (via Groq API) automatically extracts subjects, exam dates, grade weightages, and chapter outlines.
- **Urgency-Based Priority Scheduling**: Uses a deterministic algorithm to rank exam urgency:
  $$\text{Priority Score} = \left( \frac{\text{Weightage}}{\text{Days until Exam}} \right) \times 100$$
  Subjects are dynamically categorized into **Exam Looming** (High Urgency), **Revision Zone** (Medium Urgency), or **Standard** focus.
- **Customizable Daily Limits**: Dynamically scales study times to fit your daily schedule (from 1 to 12 hours) while ensuring at least 20 minutes are allocated to minor/low-priority topics.
- **Beautiful Workspace Dashboard**: Built with Streamlit using a premium, custom CSS design system inspired by modern flat-structuralism (dynamic slide-up animations, bento grid layout, responsive typography).
- **One-Click PDF Export**: Download a high-resolution, print-ready PDF timetable of your weekly schedule.
- **Automated Email Nudges**: Connects to Gmail SMTP to send daily summaries of scheduled study topics, note tips, and warnings for exams occurring within 14 days.

---

## 🛠️ Tech Stack

- **Framework**: [Streamlit](https://streamlit.io/) (Python web app engine)
- **AI Core**: [Groq Cloud API](https://wow.groq.com/) (running high-speed Llama models)
- **PDF Generation**: [ReportLab](https://www.reportlab.com/) (flowable document layouts)
- **Email Dispatch**: Standard SMTP Protocol (`smtplib`)
- **Unit Testing**: [Pytest](https://docs.pytest.org/)

---

## 📁 Repository Structure

```directory
StudyPilot/
├── app.py              # Main Streamlit web interface & configuration
├── extract.py          # PDF parsing & AI structured extraction of syllabus JSON
├── planner.py          # Priority calculation & time allocation algorithms
├── pdf_export.py       # Flowable table PDF generation module
├── reminder.py         # Daily email dispatcher & exam warnings email builder
├── test_planner.py     # Pytest unit tests for time and priority calculations
├── requirements.txt    # Application dependencies
├── DESIGN.md           # Visual standards & styling token documentation
└── README.md           # This project guide
```

---

## 🚀 Installation & Local Setup

### Prerequisites
- Python 3.10 or higher installed.
- A free [Groq API Key](https://console.groq.com/).
- A Gmail account with an [App Password](https://support.google.com/accounts/answer/185833) (if enabling email nudges).

### Step 1: Clone the Repository
```bash
git clone https://github.com/Rehansheikh787/StudyPilot.git
cd StudyPilot
```

### Step 2: Install Dependencies
It is highly recommended to use a virtual environment:
```bash
python -m venv .venv
# On Windows
.venv\Scripts\activate
# On macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### Step 3: Configure Environment Variables
Create a file named `.env` in the root directory and add the following keys:
```env
GROQ_API_KEY=your_groq_api_key_here
EMAIL_ID=your_sender_gmail@gmail.com
EMAIL_PASSWORD=your_gmail_app_password
RECEIVER_EMAIL=your_recipient_email@gmail.com
```

### Step 4: Run the Application
Start the Streamlit development server:
```bash
streamlit run app.py
```
Open your browser and navigate to `http://localhost:8501`.

---

## 🧪 Running Unit Tests

To run the unit tests and verify the scheduling core, run:
```bash
pytest test_planner.py -v
```

---

## ☁️ Deploying to Streamlit Community Cloud

You can host this application for free on Streamlit Community Cloud:

1. Push your code to your GitHub repository.
2. Visit [Streamlit Community Cloud](https://share.streamlit.io/) and connect your GitHub account.
3. Click **"New App"** and select the `StudyPilot` repository, `main` branch, and `app.py` as the entry file.
4. **Important**: Open **Advanced Settings** before deploying, and input your `.env` variables under the **Secrets** section:
   ```toml
   GROQ_API_KEY = "your_groq_api_key"
   EMAIL_ID = "your_sender_gmail@gmail.com"
   EMAIL_PASSWORD = "your_gmail_app_password"
   RECEIVER_EMAIL = "your_recipient_email@gmail.com"
   ```
5. Click **"Deploy"** and your AI Study Planner will be live online!
