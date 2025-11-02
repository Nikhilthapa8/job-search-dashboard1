# 🚀 Multi-Platform Job Search Dashboard

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)](https://github.com)

A powerful, automated job search application that helps you find and track job opportunities across **LinkedIn** and **Naukri**. Features a responsive web dashboard that works seamlessly on both desktop and mobile devices.

![Dashboard Preview](screenshots/dashboard.png)

---

## ✨ Features

### 🎯 Core Features
- **Multi-Platform Search**: Search jobs on LinkedIn and Naukri simultaneously
- **Smart Filtering**: Filter jobs by keywords, location, and job title
- **Easy Apply Detection**: Identifies LinkedIn "Easy Apply" jobs
- **Resume Management**: Upload and manage your resume
- **Application Logging**: Track all jobs you've viewed with timestamps
- **Persistent Sessions**: Stay logged in using Chrome profiles

### 🌐 Web Dashboard
- **Responsive Design**: Works perfectly on PC, tablet, and mobile
- **Real-time Search**: Instant job results from multiple platforms
- **Modern UI**: Clean, professional interface with LinkedIn-inspired design
- **Mobile Optimized**: Touch-friendly cards on mobile, table view on desktop

### 🔒 Privacy & Security
- **Local Storage**: All credentials stored locally on your machine
- **Session Management**: Reuse browser sessions to stay logged in
- **No Data Collection**: Your data never leaves your computer

---

## 📋 Table of Contents

- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Configuration](#-configuration)
- [Usage Guide](#-usage-guide)
- [Building Executables](#-building-executables)
- [Troubleshooting](#-troubleshooting)
- [FAQ](#-faq)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🔧 Installation

### Prerequisites
- **Python 3.9 or higher**
- **Google Chrome** browser installed
- **Windows, macOS, or Linux**

### Step 1: Clone the Repository
```bash
git clone https://github.com/yourusername/job-search-dashboard.git
cd job-search-dashboard
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Install Playwright Browsers
```bash
python -m playwright install chromium
```

### Step 4: Run the Application
```bash
python auto_apply_jobs_multi_platform.py
```

The dashboard will automatically open at `http://127.0.0.1:5000`

---

## 🚀 Quick Start

### First Time Setup

1. **Launch the Application**
   ```bash
   python auto_apply_jobs_multi_platform.py
   ```

2. **Configure Credentials**
   - Click "⚙️ Settings" in the top right
   - Enter your LinkedIn email and password
   - Enter your Naukri email and password
   - Upload your resume (PDF, DOC, or DOCX)
   - Click "💾 Save Settings"

3. **Start Searching**
   - Return to the dashboard
   - Select platform (LinkedIn, Naukri, or All)
   - Enter job keyword (e.g., "MIS Executive")
   - Enter location (e.g., "India")
   - Click "🔍 Search Jobs"

4. **Apply to Jobs**
   - Browse results
   - Click "📝 Apply Now" to open job in browser
   - Complete application process

---

## ⚙️ Configuration

### Settings Overview

#### Platform Credentials
- **LinkedIn Email & Password**: Required for LinkedIn job search
- **Naukri Email & Password**: Required for Naukri job search

#### Search Preferences
- **Default Location**: Your preferred job location (e.g., "India", "Bangalore")
- **Keywords**: Semicolon-separated job titles (e.g., "MIS Executive;Business Analyst")
- **Title Filter Keywords**: Only show jobs matching these terms in the title

#### Chrome Settings
- **Use Chrome Profile**: Stay logged in between sessions (recommended)
- **Chrome Profile Path**: Path to your Chrome user data
  - Windows: `C:\Users\YourName\AppData\Local\Google\Chrome\User Data`
  - macOS: `~/Library/Application Support/Google/Chrome`
  - Linux: `~/.config/google-chrome`
- **Chrome Executable Path**: Custom Chrome installation location
- **Remote Debugging**: Connect to existing Chrome window (advanced)
- **Headless Mode**: Run browser invisibly in background

### Finding Your Chrome Profile Path

**Windows:**
1. Press `Win + R`
2. Type `%LOCALAPPDATA%\Google\Chrome\User Data`
3. Copy this path to settings

**macOS:**
```bash
~/Library/Application Support/Google/Chrome
```

**Linux:**
```bash
~/.config/google-chrome
```

---

## 📖 Usage Guide

### Searching for Jobs

#### Search All Platforms
```
Platform: All Platforms
Keyword: MIS Executive
Location: India
```

#### Search Specific Platform
```
Platform: LinkedIn (or Naukri)
Keyword: Business Analyst
Location: Bangalore
```

### Understanding Results

**Desktop View:**
- Table format with sortable columns
- Platform badges (LinkedIn/Naukri)
- Easy Apply indicators
- Direct apply buttons

**Mobile View:**
- Card-based layout
- Touch-optimized buttons
- Swipeable interface
- Full job details

### Application Tracking

All job applications are logged to `applied_jobs_log.csv`:
- Platform (LinkedIn/Naukri)
- Keyword used
- Location searched
- Job title
- Job URL
- Status (Viewed/Applied)
- Timestamp

---

## 🏗️ Building Executables

### Windows EXE

#### Method 1: Using Build Script (Recommended)
```bash
# Run the included build script
build_exe.bat
```

#### Method 2: Manual Build
```bash
# Install PyInstaller
pip install pyinstaller

# Build executable
pyinstaller --onefile --windowed --name "JobSearchDashboard" auto_apply_jobs_multi_platform.py

# EXE will be in dist/ folder
```

#### Distribution Package
```
JobSearchDashboard/
├── JobSearchDashboard.exe
├── README.txt
├── SETUP_INSTRUCTIONS.txt
└── settings.json (optional)
```

### macOS App

```bash
# Create macOS application bundle
pyinstaller --onefile --windowed --name "JobSearchDashboard" --icon=icon.icns auto_apply_jobs_multi_platform.py
```

### Linux Binary

```bash
# Create Linux executable
pyinstaller --onefile --name "JobSearchDashboard" auto_apply_jobs_multi_platform.py
```

---

## 📱 Mobile Access

### Option 1: Progressive Web App (PWA) - Recommended

1. **Deploy to Cloud**
   - Use Railway.app, Heroku, or PythonAnywhere
   - See [DEPLOYMENT.md](docs/DEPLOYMENT.md) for details

2. **Add to Home Screen**
   - Open deployed URL on mobile
   - Tap browser menu
   - Select "Add to Home Screen"
   - App works like native!

### Option 2: Local Network Access

```bash
# Run on local network
python auto_apply_jobs_multi_platform.py

# Access from phone
# Open: http://YOUR_PC_IP:5000
```

Find your PC IP:
- **Windows**: `ipconfig` → IPv4 Address
- **macOS/Linux**: `ifconfig` → inet address

---

## 🔍 Troubleshooting

### Browser Not Visible During Testing

**Solution:**
1. Open `auto_apply_jobs_multi_platform.py`
2. Find line ~37: Change `"HEADLESS": True` to `"HEADLESS": False`
3. Or uncheck "Run headless" in Settings page

### Login Fails

**LinkedIn:**
- Check credentials are correct
- Disable 2FA temporarily
- Try manual login in Chrome first

**Naukri:**
- Verify email/password
- Check for CAPTCHA requirement
- Use Chrome profile to stay logged in

### No Jobs Found

**Possible Causes:**
1. **Keywords too specific** - Try broader terms
2. **Location mismatch** - Use common location names
3. **Title filters too strict** - Remove or relax filters
4. **Platform not configured** - Check credentials in Settings

### Chrome Profile Issues

**Error: "Failed to load Chrome profile"**

**Solution:**
1. Close all Chrome windows completely
2. Find correct profile path (see Configuration section)
3. Copy exact path to Settings
4. Try again

### Port 5000 Already in Use

**Solution:**
```python
# Change port in code (last line)
app.run(debug=False, port=5001, threaded=True)
```

---

## 💡 Tips & Best Practices

### For Best Results

1. **Use Chrome Profile**
   - Saves login sessions
   - Faster searches
   - No repeated logins

2. **Keyword Strategy**
   - Start broad, refine later
   - Use multiple keywords separated by semicolons
   - Include variations (e.g., "MIS;Management Information System")

3. **Title Filtering**
   - Leave empty to see all jobs
   - Add specific terms to focus results
   - Use lowercase for matching

4. **Regular Updates**
   - Update resume regularly
   - Check for new versions
   - Clear old logs periodically

### Performance Optimization

- **Close unused browser tabs** when running
- **Run in headless mode** for faster searches (after testing)
- **Limit keywords** to 3-5 most relevant terms
- **Use good internet connection** for reliable results

---

## 🐛 Known Issues

### Current Limitations

1. **Playwright on Android**: Native Android APK with Playwright is not supported
   - **Workaround**: Use PWA or cloud-hosted version
   
2. **CAPTCHA Handling**: Some sites may require manual CAPTCHA solving
   - **Workaround**: Use Chrome profile with saved sessions

3. **Rate Limiting**: Platforms may throttle automated requests
   - **Workaround**: Add delays between searches, use headless=False

### Planned Features

- [ ] Email notifications for new jobs
- [ ] Resume keyword optimization
- [ ] Application status tracking
- [ ] Interview scheduling integration
- [ ] More job platforms (Indeed, Glassdoor)

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Playwright** - Browser automation framework
- **Flask** - Web framework
- **LinkedIn & Naukri** - Job platforms

---

## 📧 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/job-search-dashboard/issues)
- **Email**: your.email@example.com
- **Documentation**: [Full Docs](docs/README.md)

---

## 📊 Project Stats

![GitHub Stars](https://img.shields.io/github/stars/yourusername/job-search-dashboard?style=social)
![GitHub Forks](https://img.shields.io/github/forks/yourusername/job-search-dashboard?style=social)
![GitHub Issues](https://img.shields.io/github/issues/yourusername/job-search-dashboard)

---

**Made with ❤️ for Job Seekers**

*Happy Job Hunting! 🎯*