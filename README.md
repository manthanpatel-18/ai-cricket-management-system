# 🏏 AI-Driven Sports Management System

A full-stack web application that combines **team management, match scheduling, performance analytics, match outcome prediction, player scouting, and a basic chatbot** into one unified sports-tech platform.

Built step-by-step over **8 weeks** with a strong focus on **real-world workflows, analytics, and user experience**.

---

## 🚀 Project Overview

Managing sports teams goes beyond scheduling matches—it involves tracking performance, analyzing outcomes, scouting talent, and making data-driven decisions.

This project simulates how a modern sports management platform works by bringing together:

- Structured team & match management  
- Data analytics dashboards  
- Machine learning–based match prediction  
- Performance-based player scouting  
- A basic assistant chatbot for interaction  

---

## ✨ Key Features

### 🔐 User Authentication
- Secure user registration & login  
- Password hashing using **Werkzeug**  
- Session-based authentication  

---

### 👥 Team Management
- Create, edit, view, and delete teams  
- Upload team logos  
- Add players with profile pictures  
- View team details in a structured dashboard  

---

### 📅 Match Scheduling System
- Schedule matches between teams  
- Match request workflow:
  - Pending  
  - Accepted  
  - Rejected  
- Match history tracking  

---

### 📊 Match Analytics Dashboard
- Visualize match insights using **Chart.js**  
- Bar & line charts for score progression  
- Pie charts for score comparison  
- Clear, user-friendly analytics views  

---

### 🤖 Match Winner Prediction
- Machine learning model trained on past match statistics  
- Predicts likely winner before a match begins  
- Adds intelligence and strategy to match planning  

---

### ⭐ MVP & Player Performance Tracking
- Track runs and wickets  
- Identify top-performing players  
- MVP section using **MongoDB aggregation pipelines**  

---

### 🔍 Player Scouting Module
- JSON API to fetch top players based on performance  
- Ranked using MongoDB aggregations  
- Helps shortlist talent directly from the dashboard  

---

### 💬 Rule-Based Chatbot
- Simple keyword-based chatbot  
- Assists users with basic queries  
- Designed to be extendable with NLP tools (Dialogflow / OpenAI)  

---

## 🛠️ Tech Stack

### Backend
- Python (Flask)  
- MongoDB (PyMongo)  
- Machine Learning (basic predictive model)  

### Frontend
- HTML + Jinja2 Templates  
- CSS (Dark UI)  
- Bootstrap  
- JavaScript  
- Chart.js  

### Other Tools
- Werkzeug (Security)  
- Font Awesome  
- MongoDB Aggregation Framework  

---

## 📂 Project Structure
```
ai-driven-sports-management-system/
│
├── app.py
├── templates/
│ ├── home.html
│ ├── login.html
│ ├── register.html
│ ├── dashboard.html
│ ├── team_details.html
│ ├── edit_team.html
│ ├── match_request.html
│ └── team_achievements.html
│
├── static/
│ ├── css/
│ │ └── style.css
│ └── uploads/
│
├── requirements.txt
└── README.md
```

## ⚙️ How to Run Locally

### 1️⃣ Clone the repository
```bash
git clone https://github.com/your-username/ai-driven-sports-management-system.git
cd ai-driven-sports-management-system
```
### 2️⃣ Install dependencies
```
pip install -r requirements.txt
```
### 3️⃣ Ensure MongoDB is running locally
```
mongodb://localhost:27017
```
### 4️⃣ Run the application
```
python app.py
```
### 5️⃣ Open in browser
```
http://127.0.0.1:5000
```
## 📸 Screenshots & Demo

Screenshots and demo video are included in the LinkedIn walkthrough, showcasing:
- Authentication flow
- Team management UI
- Match scheduling
- Analytics dashboards
- Prediction results
- Player scouting & chatbot

## 🔮 Future Enhancements

- Advanced ML models for predictions
- NLP-powered chatbot
- Role-based access (Admin / Manager)
- Live match scoring
- Cloud deployment (AWS / Azure)
- REST APIs for mobile apps

## 🎯 What I Learned

- Designing systems beyond CRUD
- Applying data analytics in real products
- Using MongoDB aggregations effectively
- Bridging ML concepts with user-facing features
- Thinking from a product & user-experience perspective

## 👤 Author

**Manthan Patel**
- Linkedin: [Manthan Patel](https://www.linkedin.com/in/manthan-patel18)
- Portfolio: [yourwebsite.com](https://yourwebsite.com)
