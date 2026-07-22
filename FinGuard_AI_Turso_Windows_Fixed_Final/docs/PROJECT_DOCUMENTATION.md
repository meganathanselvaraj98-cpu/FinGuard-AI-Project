# Project Documentation

## Problem

Users often lack a consolidated view of spending, savings, bank statements, recurring costs, risk and future cash flow.

## Objective

Provide a secure local website that stores financial information in SQLite, cleans statements, visualizes behaviour, applies machine learning, generates explainable guidance and allows users to inspect and export their own stored data.

## Scope

- Authentication and encrypted profile/account management
- Multi-statement transaction ingestion
- Analytics, budgets, predictions, health score, advisor and investment education
- Report generation and audit history
- User data centre and administrator SQLite viewer
- FastAPI, Docker and automated tests

## Database workflow

`data/finguard_ai.db` is created automatically. SQLAlchemy creates all tables and seeds finance categories. Every business write runs in a transaction. Failed writes roll back. Foreign keys enforce ownership links and cascading deletion.
