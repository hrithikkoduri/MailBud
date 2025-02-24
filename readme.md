# MailBud

<div align="center">
  <!-- Backend -->
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/Anthropic-6B4FBB?style=for-the-badge&logo=anthropic&logoColor=white" />
  <img src="https://img.shields.io/badge/LangChain-121212?style=for-the-badge&logo=chainlink&logoColor=white" />
  <img src="https://img.shields.io/badge/LangGraph-FF6B6B?style=for-the-badge&logo=graph&logoColor=white" />
  <img src="https://img.shields.io/badge/Gmail_API-EA4335?style=for-the-badge&logo=gmail&logoColor=white" />
  <img src="https://img.shields.io/badge/Google_Calendar_API-4285F4?style=for-the-badge&logo=google-calendar&logoColor=white" />
  
  <!-- Frontend -->
  <img src="https://img.shields.io/badge/Next.js-000000?style=for-the-badge&logo=next.js&logoColor=white" />
  <img src="https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white" />
  <img src="https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white" />
  <img src="https://img.shields.io/badge/React-61DAFB?style=for-the-badge&logo=react&logoColor=black" />

  <h3>Your AI Assistant for Email & Calendar Management 📧📅</h3>

  <p align="center">
    <b>Automated Meeting Scheduling | Smart Calendar Management | Conflict Resolution | Real-time Updates</b>
  </p>
</div>

## Overview
MailBud is an intelligent AI assistant that streamlines email management and meeting scheduling. It automatically scans your Gmail inbox, identifies meeting requests, and handles calendar scheduling while managing conflicts - all through an intuitive interface.

## Overview
MailBud is an intelligent AI assistant that streamlines email management and meeting scheduling. It automatically scans your Gmail inbox, identifies meeting requests, and handles calendar scheduling while managing conflicts - all through an intuitive interface.

## Key Features

- **Automated Email Analysis**: Scans Gmail inbox to identify and extract meeting requests
- **Smart Calendar Management**: Automatically detects and handles calendar conflicts
- **Interactive Resolution**: Provides options to resolve scheduling conflicts
- **Real-time Updates**: Streams progress and status updates during processing
- **Google Calendar Integration**: Creates calendar events and sends invites to attendees
- **Video Conference Integration**: Automatically adds Google Meet links to scheduled meetings

## Architecture & How it Works
![Image](https://github.com/user-attachments/assets/00edac40-6b2f-4999-b480-fa2ca1a0e46d)


### Process Flow:
1. User initiates meeting fetch through the frontend interface
2. Backend authenticates with Google services
3. Email threads are retrieved and analyzed by Claude 3.5
4. Meeting details are extracted and checked for conflicts
5. User can select meetings and resolve conflicts
6. Selected meetings are scheduled with Google Calendar
7. Real-time updates are streamed to the frontend

## Setup Instructions

### Prerequisites
- Python 3.12+
- Node.js 18+
- Google Cloud Platform account
- Anthropic API key

### Backend Setup
1. Clone the repository
```bash
git clone https://github.com/yourusername/mailbud.git
cd mailbud
cd backend
```
2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate
```
3. Install dependencies:
```bash
pip install -r requirements.txt
```


4. Set up environment variables:
```bash
cp .env.example .env
```
Edit the `.env` file with your credentials and API keys.
```bash
ANTHROPIC_API_KEY=your_anthropic_api_key
```

5. Set up Google OAuth credentials:
- Create a project in Google Cloud Console
- Enable Gmail and Calendar APIs
- Create OAuth 2.0 credentials
- Download credentials and save as `credentials.json` in the backend directory

6. Start the backend server:
Open a new terminal and run the following command:
```bash
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup
1. Install dependencies:
Open a new terminal, make sure you are in the MailBud directory and run the following command:
```bash
cd frontend
npm install
```
2. Start the frontend application:
Open a new terminal and run the following command:
```bash
npm run dev
```

## Contributing
Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


---

Made with ❤️ by [@hrithikkoduri](https://github.com/hrithikkoduri)



