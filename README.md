# Recruitment Agent System (v2.0)
### Developed by SANDKHU SOFTWARE

A secure, multi-user desktop application designed to streamline candidate management, CV storage, and reporting for South African recruitment agencies and SMEs. 

## The Problem
Most SMEs and small recruitment agencies manage candidates through spreadsheets, WhatsApp messages, and paper CVs. This leads to lost records, slow turnaround times, and poor compliance with the Protection of Personal Information Act (POPIA).

## The Solution
The Recruitment Agent System provides a centralized, secure database for candidate management. It features role-based access control, automated PDF/Excel reporting, and secure CV storage. 

## Key Features
- **Secure Authentication:** Passwords are hashed using Bcrypt with automatic salting.
- **Account Lockout:** Accounts lock for 15 minutes after 5 failed login attempts to prevent brute-force attacks.
- **Role-Based Access:** Distinct 'Admin' and 'User' roles to restrict access to sensitive data.
- **Live Search:** Instantly filter candidates by name, ID number, phone, or email.
- **Automated Reporting:** Export candidate shortlists to professional Excel and PDF formats with one click.
- **Cross-Platform:** Packaged as standalone executables for Windows (.exe) and macOS (.app).

## Tech Stack
- **Language:** Python 3
- **GUI Framework:** Tkinter
- **Database:** SQLite
- **Security:** Bcrypt
- **Reporting:** ReportLab (PDF), OpenPyXL (Excel)
- **Packaging:** PyInstaller

## Vision
SANDKHU SOFTWARE is a youth-driven tech company. Our mission is to build world-class software solutions while mentoring the next generation of South African developers.
