FinGuard AI — Next-Generation Personal Finance Intelligence System

<p align="center">
  <strong>Secure financial tracking, analytics, forecasting, anomaly detection, and personalized guidance in one intelligent platform.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white" alt="Python 3.12">
  <img src="https://img.shields.io/badge/Streamlit-Frontend-FF4B4B?logo=streamlit&logoColor=white" alt="Streamlit">
  <img src="https://img.shields.io/badge/Turso-Cloud%20Database-4FF8D2" alt="Turso">
  <img src="https://img.shields.io/badge/SQLAlchemy-ORM-D71F00?logo=sqlalchemy&logoColor=white" alt="SQLAlchemy">
  <img src="https://img.shields.io/badge/Scikit--learn-Machine%20Learning-F7931E?logo=scikitlearn&logoColor=white" alt="Scikit-learn">
  <img src="https://img.shields.io/badge/Plotly-Interactive%20Charts-3F4F75?logo=plotly&logoColor=white" alt="Plotly">
  <img src="https://img.shields.io/badge/Status-Active%20Development-yellow" alt="Status">
</p>

Project Overview

FinGuard AI is a secure personal finance intelligence platform developed using Python and Streamlit.

The application allows users to upload transaction data, analyse income and expenses, review spending behaviour, estimate future expenses and savings, detect unusual transactions, calculate a Financial Health Score, and receive personalized financial guidance.

Unlike a basic expense tracker, FinGuard AI converts raw transaction records into meaningful dashboards, predictions, risk indicators, and actionable financial insights.

FinGuard AI is developed for academic, research, portfolio, and educational purposes. Financial and investment-related outputs are informational and must not be treated as professional financial advice.

Problem Statement

Digital payments through UPI, cards, online shopping, subscriptions, and multiple bank accounts have made financial activity more convenient but harder to track.

Many users do not have a clear understanding of where their money is being spent, whether monthly expenses are increasing, how much they are saving, whether a transaction is unusual, or how current financial behaviour may affect their future.

Most traditional finance applications focus mainly on transaction history. They may not provide integrated analytics, financial health scoring, machine-learning predictions, unusual-activity detection, or personalized recommendations.

FinGuard AI addresses this gap by providing a centralized, intelligent, and user-friendly personal finance platform.

Objectives

Securely register and authenticate users.

Store each user’s financial records separately.

Support CSV, Excel, text-based PDF, and manual transaction entry.

Clean and standardize uploaded transaction data.

Analyse income, expenses, savings, cash flow, categories, merchants, and payment methods.

Predict future expenses and estimated savings.

Detect unusual transactions using machine learning.

Analyse financial risk and spending behaviour.

Calculate an explainable Financial Health Score.

Provide personalized budget, savings, subscription, and investment-learning suggestions.

Generate downloadable financial reports.

Provide role-based access for users and administrators.

Key Features

Authentication and User Management

Secure user registration and login

Password hashing using Argon2

JWT-based authentication

Role-based access control

Normal-user and administrator workspaces

User-scoped transaction access

Secure session handling

User preferences and profile settings

Account and Transaction Management

Multiple bank-account support

CSV transaction upload

Excel transaction upload

Text-based PDF statement upload

Manual income and expense entry

Transaction validation and cleaning

Duplicate transaction handling

Merchant and category management

Statement-wise and account-wise views

Transaction search and filtering

Dashboard and Analytics

Total income

Total expenses

Net savings

Savings rate

Current balance

Financial Health Score

Transaction count

Monthly income, expense, and savings trends

Category-wise spending

Payment-mode analysis

Top-merchant analysis

Weekday spending analysis

Cash-flow progression

Bank-balance trend

Interactive filters and charts

Machine Learning and Intelligence

Expense forecasting

Savings prediction

Category-pattern analysis

Financial-risk classification

Isolation Forest-based anomaly detection

Model-performance comparison

Confusion-matrix visualization

Unusual-transaction scoring

Personalized financial recommendations

Financial Wellness

Financial Health Score from 0 to 100

Savings-rate analysis

Expense-stability analysis

Budget-behaviour analysis

Category-diversification analysis

Subscription-candidate detection

Expense-reduction simulator

Educational investment-allocation ideas

Goal, risk-preference, and time-horizon settings

Reports and Exports

Transaction report generation

CSV export

Excel export

PDF report support

Chart download support

User-specific financial summaries

Cloud-mode export guidance

Local backup support where applicable

Application Modules

1. Authentication and Access Control

Handles registration, login, password hashing, JWT authentication, user sessions, role validation, and administrator access.

2. Bank Account and Statement Management

Allows users to create bank-account profiles and upload financial statements in supported formats.

3. Transaction Processing

Validates, cleans, standardizes, categorizes, stores, filters, and displays transaction records.

4. Dashboard and Financial Analytics

Provides KPIs, monthly summaries, category analytics, merchant analysis, payment-mode insights, and cash-flow visualizations.

5. Prediction and Machine Learning

Provides expense forecasting, savings estimation, category analysis, financial-risk classification, and unusual-transaction detection.

6. Financial Health and Advisor

Calculates a financial health score and provides personalized savings, budget, subscription, and financial-discipline recommendations.

7. Reports and Settings

Allows users to export financial data, manage preferences, configure investment-learning inputs, and review account settings.

8. Administrator Portal

Allows authorized administrators to review users, accounts, transactions, predictions, and overall system information.

System Workflow

User Registration / Login
            |
            v
Password Hash Verification
            |
            v
JWT Authentication and Role Validation
            |
            v
Create Bank Account / Select Existing Account
            |
            v
Upload CSV, Excel, Text-Based PDF
or Add Transaction Manually
            |
            v
File and Data Validation
            |
            v
Transaction Cleaning and Standardization
            |
            v
Category and Merchant Processing
            |
            v
Turso Cloud Database Storage
            |
            v
User-Scoped Data Retrieval
            |
            v
Dashboard and Interactive Analytics
            |
            v
Machine Learning Processing
            |
            +-----------------------------+
            | Expense Forecast            |
            | Savings Prediction          |
            | Category Analysis           |
            | Financial Risk Analysis     |
            | Unusual Activity Detection  |
            +-----------------------------+
            |
            v
Financial Health Score
            |
            v
AI-Assisted Recommendations
            |
            v
Reports and Data Export

Technology Stack

Component

Technology

User Interface

Streamlit

Programming Language

Python 3.12

Database

Turso Cloud Database

Local Development Database

SQLite-compatible local replica

ORM

SQLAlchemy

Turso Client

libSQL

Data Analysis

Pandas, NumPy

Machine Learning

Scikit-learn

Interactive Charts

Plotly

Statistical Charts

Matplotlib

Excel Processing

Pandas, OpenPyXL

PDF Processing

PyMuPDF

Password Security

Argon2

Authentication

PyJWT

Sensitive Data Protection

Python Cryptography

Configuration

Streamlit Secrets and environment variables

Development Environment

VS Code

Version Control

Git and GitHub

Deployment Target

Streamlit Community Cloud

System Architecture

+------------------------------------------------------+
|                 Streamlit User Interface             |
| Dashboard | Upload | Analytics | Predictions | Admin |
+----------------------------+-------------------------+
                             |
                             v
+------------------------------------------------------+
|                   Python Application Layer           |
| Validation | Authentication | Services | Reporting   |
+----------------------------+-------------------------+
                             |
              +--------------+--------------+
              |                             |
              v                             v
+----------------------------+  +----------------------------+
| Financial Analytics Layer  |  | Machine Learning Layer     |
| Pandas | NumPy | KPIs       |  | Forecasting | Anomalies   |
| Categories | Cash Flow      |  | Classification | Scoring  |
+----------------------------+  +----------------------------+
              |                             |
              +--------------+--------------+
                             |
                             v
+------------------------------------------------------+
|                SQLAlchemy Data Access Layer          |
+----------------------------+-------------------------+
                             |
                             v
+------------------------------------------------------+
|                   Turso Cloud Database               |
| Users | Accounts | Statements | Transactions         |
| Preferences | Predictions | Budgets | Audit Data     |
+------------------------------------------------------+

Machine Learning Features

Expense Forecasting

The forecasting module studies historical monthly expense patterns and estimates upcoming expenses.

Possible models compared by the application include:

Linear Regression
Decision Tree Regressor
Random Forest Regressor
K-Nearest Neighbours Regressor
Support Vector Regressor
Gradient Boosting Regressor

The system may compare models using:

MAE  - Mean Absolute Error
RMSE - Root Mean Squared Error

Savings Prediction

Estimated Savings = Expected Income - Predicted Expense

Category Analysis

The system analyses transaction descriptions and labelled categories to identify category patterns and evaluate classification quality.

Financial Risk Classification

Financial-risk indicators are generated from transaction behaviour, spending patterns, and financial stability signals.

The result is educational and must not be interpreted as an official fraud decision, credit score, or lending assessment.

Unusual Activity Detection

Isolation Forest is used to identify transactions that differ from the user’s normal spending behaviour.

An unusual transaction is a statistical outlier and is not automatic proof of fraud.

Financial Health Score

FinGuard AI calculates an explainable score between 0 and 100.

Component

Purpose

Savings Rate

Measures the percentage of income retained

Expense Stability

Measures consistency of monthly expenses

Budget Behaviour

Reviews spending against planned limits

Transaction Risk

Considers risky or unusual activity

Category Diversification

Reviews concentration of spending

Financial Discipline

Measures consistency of positive habits

Example Classification

Score

Financial Status

75–100

Strong Financial Health

50–74

Moderate Financial Health

0–49

Financial Pressure Detected

Savings Rate = (Net Savings / Total Income) × 100

Dashboard Views

Main Dashboard

Overview

Spending

Cash flow

Recent transactions

Analytics Workspace

Trends

Categories

Behaviour

Risk and anomaly

Statistical views

Prediction Workspace

Prediction readiness

Expense and savings forecast

Category insights

Financial risk

Unusual activity

Financial Wellness

Financial Health Score

Score-contribution chart

Personalized financial guidance

Subscription alerts

Expense-reduction simulation

Investment Learning

Risk-preference selection

Investment-horizon selection

Goal selection

Investable-surplus estimate

Educational allocation illustration

Contribution scenario calculator

Dataset

FinGuard AI can be tested using synthetic transaction data to avoid exposing real financial information.

A test dataset may include:

10,000 synthetic transactions

Salary and freelance income

Rent and utility payments

Groceries and food expenses

Shopping and healthcare expenses

Education and travel expenses

Subscriptions and investments

Different payment modes

Running balances

Intentional high-value transactions for anomaly testing

Recommended Columns

transaction_id
transaction_date
description
transaction_type
amount
balance_after
category
payment_mode
merchant

Do not upload real bank account numbers, card numbers, UPI IDs, customer IDs, authentication tokens, encryption keys, or real bank statements to a public repository.

Project Structure

FinGuard_AI/
│
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
│
├── .streamlit/
│   ├── config.toml
│   └── secrets.toml
│
├── backend/
│   ├── analytics.py
│   ├── config.py
│   ├── database.py
│   ├── ml_service.py
│   ├── models.py
│   ├── security.py
│   ├── services.py
│   └── sqlite_manager.py
│
├── frontend/
│   ├── charting.py
│   ├── components.py
│   ├── theme.py
│   └── pages/
│       ├── dashboard.py
│       ├── intelligence.py
│       ├── reports.py
│       └── additional application pages
│
├── scripts/
│   └── test_turso_connection.py
│
├── data/
│   ├── sample/
│   └── local Turso replica files
│
└── tests/

The exact file structure may change as new modules are added.

Installation

Prerequisites

Python 3.12, 64-bit

VS Code

Git, optional

A Turso database

A Turso read-and-write authentication token

1. Clone or Download the Project

git clone https://github.com/your-username/finguard-ai.git
cd finguard-ai

2. Create a Virtual Environment

py -3.12 -m venv .venv

Activate it:

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1

Verify:

python --version

Expected:

Python 3.12.x

3. Install Dependencies

python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt

4. Verify Important Packages

python -c "import streamlit; print('Streamlit ready')"
python -c "import sqlalchemy; print('SQLAlchemy ready')"
python -c "import libsql; print('libSQL ready')"
python -c "import jwt; print('PyJWT ready')"
python -c "from argon2 import PasswordHasher; print('Argon2 ready')"

Environment Configuration

Create:

.streamlit/secrets.toml

Add:

TURSO_DATABASE_URL = "libsql://your-database-name.turso.io"
TURSO_AUTH_TOKEN = "your-read-write-token"

SECRET_KEY = "your-secure-secret-key"
HASH_PEPPER = "your-secure-password-pepper"
FIELD_ENCRYPTION_KEY = "your-field-encryption-key"

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "your-strong-admin-password"

COOKIE_SECURE = false

For cloud deployment:

COOKIE_SECURE = true

Security Rules

Never commit secrets.toml to GitHub.

Never publish Turso authentication tokens.

Never change the field-encryption key after storing encrypted data.

Use the same encryption key in local and deployed environments.

Recommended .gitignore:

.venv/
__pycache__/
*.pyc
.env
.streamlit/secrets.toml
.secrets/
data/*.db
data/*.db-*
*.db

Test the Turso Connection

python .\scripts	est_turso_connection.py

A successful test confirms that the database URL, authentication token, and required application tables are accessible.

Running the Application

python -m streamlit run .pp.py

Application URL:

http://localhost:8501

Run without activating the environment:

.\.venv\Scripts\python.exe -m streamlit run .pp.py

Stop the application:

Ctrl + C

One-Click Windows Runner

Create RUN_FINGUARD.bat:

@echo off
title FinGuard AI

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment not found.
    echo Complete the setup process first.
    pause
    exit /b 1
)

echo Starting FinGuard AI...
".venv\Scripts\python.exe" -m streamlit run app.py

pause

Security Implementation

Password Protection

Passwords are hashed using Argon2 and are never stored as plain text.

Authentication

JWT-based authentication is used to manage authenticated sessions.

Role-Based Access Control

Normal users can access only their own financial records. Administrative pages are restricted to authorized administrator accounts.

Sensitive Data Protection

Sensitive account information is masked in the interface and protected using encryption.

Account Number: ••••4582

Data Isolation

Database queries are scoped using the authenticated user ID so that one user cannot access another user’s financial records.

Deployment

The project is suitable for deployment on Streamlit Community Cloud.

Push source code to GitHub
        |
        v
Create a Streamlit Cloud application
        |
        v
Select app.py as the entry file
        |
        v
Add Turso and security values in Streamlit Secrets
        |
        v
Deploy the application

Do not upload .streamlit/secrets.toml to GitHub.

Future Enhancements

Direct bank API integration with user consent

Real-time transaction synchronization

Mobile application

Email and SMS transaction extraction

Multilingual support

Tamil voice assistant

Real-time fraud-risk notifications

Bill and EMI reminders

Goal-based savings plans

Family finance management

Shared household budgets

Explainable AI recommendations

Advanced time-series forecasting

Two-factor authentication

Automated model retraining

Limitations

Uploaded PDF files must contain extractable text unless OCR is added.

Machine-learning results depend on the quality and amount of transaction history.

Anomaly detection identifies statistical outliers and does not confirm fraud.

Forecasts are estimates and may differ from actual future spending.

Investment illustrations do not guarantee returns.

FinGuard AI is not a replacement for a bank, financial adviser, tax professional, or fraud-investigation service.

Disclaimer

FinGuard AI is an educational personal finance analytics project.

It does not provide certified financial advice.

It does not guarantee investment returns.

It does not make lending or credit decisions.

It does not confirm whether a transaction is fraudulent.

Users must verify unknown transactions with their bank.

Public demonstrations must use synthetic or anonymized data.

Author

Arish Khan A

B.Sc. Computer Science Graduate

Interested in Python Development, Data Analytics, Machine Learning, Artificial Intelligence, Web Application Development, Financial Technology, and Cybersecurity.

Acknowledgements

FinGuard AI is built using open-source technologies including Python, Streamlit, Pandas, NumPy, Scikit-learn, Plotly, Matplotlib, SQLAlchemy, Turso, libSQL, PyMuPDF, OpenPyXL, Argon2, PyJWT, and Python Cryptography.

Project Status

Project Name     : FinGuard AI
Project Type     : Personal Finance Intelligence Platform
Frontend         : Streamlit
Backend          : Python
Database         : Turso Cloud Database
ORM              : SQLAlchemy
Machine Learning : Scikit-learn
Current Status   : Active Development

<p align="center">
  <strong>FinGuard AI transforms financial transactions into clear insights, meaningful predictions, and better financial decisions.</strong>
</p>

<p align="center">
  Developed with Python, Streamlit, Data Analytics, Machine Learning, and Secure Cloud Storage.
</p>
