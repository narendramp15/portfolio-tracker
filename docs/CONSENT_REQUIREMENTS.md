# Consent Requirements for Portfolio Tracker

**Effective Date:** February 1, 2026

This document outlines the consent mechanisms required for the Portfolio Tracker Service, in compliance with the Digital Personal Data Protection Act, 2023 (DPDPA) and other applicable Indian laws. Consent must be explicit, informed, and freely given.

## 1. Types of Consent Required
- **General Service Consent**: For using the app and processing basic user data.
- **Broker Integration Consent**: For connecting and syncing data from specific brokers.
- **Data Sharing Consent**: For aggregating or sharing data across brokers (if implemented).
- **Marketing/Communications Consent**: Optional, for updates or newsletters.

## 2. Consent Collection Process
- **UI Implementation**: Consent must be obtained via clear, accessible UI elements (e.g., checkboxes, modals) before data processing.
- **Timing**: Consent requested at account creation and before each broker connection.
- **Language**: Plain, easy-to-understand language; no jargon.
- **Granularity**: Separate consents for different data types/uses.
- **Record Keeping**: Log consent timestamps and details for audit purposes.

## 3. Consent Withdrawal
- Users can withdraw consent anytime via account settings or broker disconnection.
- Upon withdrawal, data processing stops, and data is deleted (except where legally required to retain).
- Clear UI for withdrawal, with confirmation prompts.

## 4. Specific Requirements for Broker Integrations
- **Before Setup**: Display broker terms, data usage, and risks. Require checkbox: "I consent to connect my [Broker] account and sync holdings/transactions."
- **Data Scope**: Specify what data is collected (e.g., holdings, transactions, credentials).
- **Third-Party Notice**: Inform users that data is shared with the broker's API.
- **Encryption Notice**: Assure users that credentials are encrypted.

## 5. Implementation Checklist
- [ ] Add consent modal/component in frontend (e.g., React component).
- [ ] Backend validation: Check consent status before processing data.
- [ ] Database: Store consent records (e.g., user_id, consent_type, timestamp, status).
- [ ] Audit Logs: Track consent changes.
- [ ] User Dashboard: Allow viewing/managing consents.

## 6. Legal Compliance Notes
- Consent must be verifiable and not bundled with other terms.
- For minors or vulnerable users: Additional safeguards.
- Regular audits to ensure compliance.

## 7. Example UI Text
- "By checking this box, I consent to the collection and processing of my financial data from [Broker] for portfolio tracking purposes. I understand my data will be encrypted and used only as described in the Terms and Conditions."
- "I can withdraw this consent at any time by disconnecting my account."