import json
import re
import random
from datetime import datetime, timedelta
import hashlib
import streamlit as st
import pandas as pd
import plotly.express as px
from typing import Dict, List, Optional, Union, Any
import ollama
from difflib import get_close_matches
import base64
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import uuid
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from io import BytesIO
from pathlib import Path

# Load the bank data with error handling
try:
    with open('dummydata.json', 'r') as f:
        BANK_DATA = json.load(f)
except FileNotFoundError:
    st.error("Error: dummydata.json file not found!")
    st.stop()
except json.JSONDecodeError:
    st.error("Error: Invalid JSON format in dummydata.json!")
    st.stop()

# Ensure all required keys exist in BANK_DATA
REQUIRED_KEYS = ['users', 'bank_info', 'loan_products', 'government_schemes', 
                'transactions_history', 'bills', 'spending_categories', 'bot_responses',
                'account_info', 'account_requests']
for key in REQUIRED_KEYS:
    if key not in BANK_DATA:
        if key == 'account_requests':
            BANK_DATA['account_requests'] = []
        else:
            st.error(f"Error: Missing required key '{key}' in dummydata.json!")
            st.stop()

# Add default bank_accounts if not present
if 'bank_accounts' not in BANK_DATA:
    BANK_DATA['bank_accounts'] = {
        'student_account': {
            'name': 'Student Account',
            'min_balance': 0,
            'interest_rate': 2.5,
            'documents': 'Student ID, Address Proof',
            'features': 'Zero balance account, Special education loans, Discounts on student services'
        },
        'nri_account': {
            'name': 'NRI Account',
            'min_balance': 5000,
            'interest_rate': 3.5,
            'documents': 'Passport, Visa, Address Proof',
            'features': 'Foreign currency support, Global banking, Higher interest rates'
        },
        'senior_account': {
            'name': 'Senior Citizen Account',
            'min_balance': 1000,
            'interest_rate': 4.0,
            'documents': 'Age Proof, Address Proof',
            'features': 'Higher interest rates, Priority services, Special pension benefits'
        },
        'regular_savings_account': {
            'name': 'Regular Savings Account',
            'min_balance': 1000,
            'interest_rate': 3.0,
            'documents': 'ID Proof, Address Proof',
            'features': 'Free ATM withdrawals, Online banking, Monthly statements'
        }
    }

# Ensure account_info exists and is properly formatted with all required fields
if 'account_info' not in BANK_DATA:
    BANK_DATA['account_info'] = BANK_DATA.get('bank_accounts', {})

# Validate all accounts have required fields
for account_type, account_data in BANK_DATA['account_info'].items():
    account_data.setdefault('min_balance', 0)
    account_data.setdefault('interest_rate', 0)
    account_data.setdefault('documents', 'Not specified')
    account_data.setdefault('features', 'No special features')

class PDFGenerator:
    """Class to generate PDF reports using ReportLab"""
    
    @staticmethod
    def generate_pdf_report(user_data: Dict[str, Any], report_data: Dict[str, Any]) -> BytesIO:
        """Generate a PDF report with transaction details and user information"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        
        styles = getSampleStyleSheet()
        elements = []
        
        # Custom styles
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Heading1'],
            fontSize=16,
            alignment=1,  # Center alignment
            spaceAfter=12
        )
        
        header_style = ParagraphStyle(
            'Header',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=6
        )
        
        normal_style = styles['Normal']
        bold_style = styles['Heading3']
        
        # Title
        elements.append(Paragraph('CGBank - Monthly Statement Report', title_style))
        elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
        elements.append(Spacer(1, 0.5 * inch))
        
        # Account Holder Information
        elements.append(Paragraph('Account Holder Information', header_style))
        
        # User details table
        user_info = [
            ["Account Holder", user_data['name']],
            ["Account Number", user_data['account_number']],
            ["Account Type", user_data['account_type']],
            ["Report Period", f"{report_data['start_date']} to {report_data['end_date']}"],
            ["Current Balance", f"₹{user_data['balance']:,.2f}"]
        ]
        
        user_table = Table(user_info, colWidths=[2*inch, 4*inch])
        user_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey),
        ]))
        
        elements.append(user_table)
        elements.append(Spacer(1, 0.5 * inch))
        
        # Transaction Summary
        elements.append(Paragraph('Transaction Summary', header_style))
        
        summary_data = [
            ["Total Transactions", str(report_data['total_transactions'])],
            ["Total Credit", f"₹{report_data['total_credit']:,.2f}"],
            ["Total Debit", f"₹{report_data['total_debit']:,.2f}"],
            ["Net Change", f"₹{report_data['net_change']:,.2f}"]
        ]
        
        summary_table = Table(summary_data, colWidths=[3*inch, 3*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey),
        ]))
        
        elements.append(summary_table)
        elements.append(Spacer(1, 0.5 * inch))
        
        # Transaction Details
        elements.append(Paragraph('Transaction Details', header_style))
        
        # Prepare transaction data
        transaction_data = [["Date", "Description", "Amount", "Balance"]]
        for txn in report_data['transactions']:
            date_str = txn['date'].strftime('%Y-%m-%d') if isinstance(txn['date'], datetime) else txn['date']
            amount = txn['amount']
            amount_str = f"+₹{amount:,.2f}" if amount > 0 else f"-₹{abs(amount):,.2f}"
            transaction_data.append([
                date_str,
                txn['description'],
                amount_str,
                f"₹{txn['balance']:,.2f}"
            ])
        
        # Create transaction table
        transaction_table = Table(transaction_data, colWidths=[1*inch, 2.5*inch, 1.5*inch, 1.5*inch])
        transaction_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.whitesmoke]),
        ]))
        
        elements.append(transaction_table)
        elements.append(Spacer(1, 0.5 * inch))
        
        # Notes section
        notes = """
        <para>
        <font size=9><i>Note: This is an automatically generated statement. 
        For any discrepancies, please contact CGBank customer support 
        within 7 days of receiving this statement.</i></font>
        </para>
        """
        elements.append(Paragraph(notes, styles['Normal']))
        elements.append(Spacer(1, 0.2 * inch))
        elements.append(Paragraph("CGBank - Coimbatore Trusted Banking Partner", 
                                ParagraphStyle('Footer', parent=styles['Normal'], alignment=1)))
        
        # Build the PDF
        doc.build(elements)
        
        buffer.seek(0)
        return buffer

class FeedbackSystem:
    """Class to handle feedback and reviews"""
    
    @staticmethod
    def send_feedback_email(name: str, email: str, rating: int, feedback: str):
        """Send feedback email to the specified address"""
        try:
            # Email configuration
            sender_email = "cravinsanjay22@gmail.com"
            sender_password = "gror taom ymiq dhat"
            receiver_email = "cravinsanjay10@gmail.com"
            
            # Create message
            message = MIMEMultipart()
            message["From"] = sender_email
            message["To"] = receiver_email
            message["Subject"] = f"New Feedback from {name} - Rating: {rating}/5"
            
            # Email body
            body = f"""
            <h2>New Feedback Received</h2>
            <p><strong>Name:</strong> {name}</p>
            <p><strong>Email:</strong> {email}</p>
            <p><strong>Rating:</strong> {rating} stars</p>
            <p><strong>Feedback:</strong></p>
            <p>{feedback}</p>
            """
            
            message.attach(MIMEText(body, "html"))
            
            # Send email
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, receiver_email, message.as_string())
                
            return True
        except Exception as e:
            st.error(f"Error sending feedback email: {str(e)}")
            return False

class CGBankDatabase:
    """Class to interact with the bank data"""
    
    @staticmethod
    def _save_data():
        """Save the current BANK_DATA to the JSON file"""
        try:
            with open('dummydata.json', 'w') as f:
                json.dump(BANK_DATA, f, indent=2)
            return True
        except Exception as e:
            st.error(f"Error saving data: {str(e)}")
            return False
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using SHA-256 with salt"""
        salt = "CGBank_Salt_Value_123!"
        return hashlib.sha256((password + salt).encode()).hexdigest()
    
    @staticmethod
    def get_user(username: str) -> Optional[Dict[str, Any]]:
        """Get user data by username (case-insensitive)"""
        username_lower = username.lower()
        for uname, user_data in BANK_DATA['users'].items():
            if uname.lower() == username_lower:
                return user_data
        return None
    
    @staticmethod
    def verify_user(username: str, password: str) -> bool:
        """Verify user credentials""";
        user = CGBankDatabase.get_user(username)
        if not user:
            return False
        return user['password'] == password
    
    @staticmethod
    def get_bank_info() -> Dict[str, Any]:
        """Get bank information"""
        return BANK_DATA['bank_info']
    
    @staticmethod
    def get_loan_products() -> Dict[str, Any]:
        """Get loan products information"""
        return BANK_DATA['loan_products']
    
    @staticmethod
    def get_government_schemes() -> Dict[str, Any]:
        """Get government schemes information"""
        return BANK_DATA['government_schemes']
    
    @staticmethod
    def get_account_info() -> Dict[str, Any]:
        """Get account types information with proper formatting"""
        account_info = BANK_DATA.get('account_info', {})
        
        # Ensure all accounts have required fields with defaults
        for account_type, account_data in account_info.items():
            # Use the account type key to get the correct account data
            if account_type in BANK_DATA.get('bank_accounts', {}):
                account_data.update(BANK_DATA['bank_accounts'][account_type])
                
        return account_info
    
    @staticmethod
    def get_user_transactions(username: str) -> List[Dict[str, Any]]:
        """Get transaction history for a user"""
        user = CGBankDatabase.get_user(username)
        if not user:
            return []
        
        # Get transactions from session state if available
        if 'transactions' in st.session_state and st.session_state.transactions:
            return st.session_state.transactions
        
        # Otherwise generate new transactions
        transactions = []
        for txn in BANK_DATA['transactions_history']:
            transaction = {
                'date': datetime.now() - timedelta(days=random.randint(1, 30)),
                'description': txn['name'],
                'amount': txn['amt'],
                'balance': user['balance'] - random.uniform(0, 1000)
            }
            transactions.append(transaction)
        
        # Sort by date and store in session state
        transactions = sorted(transactions, key=lambda x: x['date'], reverse=True)
        st.session_state.transactions = transactions
        return transactions
    
    @staticmethod
    def get_user_bills(username: str) -> List[Dict[str, Any]]:
        """Get bills for a user"""
        return BANK_DATA['bills']
    
    @staticmethod
    def get_spending_categories(username: str) -> List[Dict[str, Any]]:
        """Get spending categories for a user"""
        return BANK_DATA['spending_categories']
    
    @staticmethod
    def add_transaction(username: str, description: str, amount: float) -> bool:
        """Add a new transaction for the user and save to JSON"""
        user = CGBankDatabase.get_user(username)
        if not user:
            return False
        
        # Get current transactions
        transactions = CGBankDatabase.get_user_transactions(username)
        
        # Create new transaction
        new_transaction = {
            'date': datetime.now(),
            'description': description,
            'amount': amount,
            'balance': user['balance'] + amount
        }
        
        # Insert at beginning of list (most recent first)
        transactions.insert(0, new_transaction)
        
        # Update user balance
        user['balance'] += amount
        
        # Add to transactions_history in BANK_DATA
        BANK_DATA['transactions_history'].append({
            'name': description,
            'amt': amount
        })
        
        # Update session state
        st.session_state.transactions = transactions
        
        # Save to JSON file
        return CGBankDatabase._save_data()
    
    @staticmethod
    def add_bill_payment(username: str, bill_name: str, amount: float) -> bool:
        """Add a bill payment transaction and update JSON"""
        user = CGBankDatabase.get_user(username)
        if not user:
            return False
        
        # Add to transactions
        success = CGBankDatabase.add_transaction(username, f"Bill Payment: {bill_name}", -amount)
        if not success:
            return False
        
        # Remove paid bill from bills list
        BANK_DATA['bills'] = [bill for bill in BANK_DATA['bills'] if bill['name'] != bill_name]
        
        # Save to JSON file
        return CGBankDatabase._save_data()
    
    @staticmethod
    def add_new_bill(username: str, bill_data: Dict[str, Any]) -> bool:
        """Add a new bill to the user's account and update JSON"""
        # Add to bills list
        BANK_DATA['bills'].append(bill_data)
        
        # Save to JSON file
        return CGBankDatabase._save_data()
    
    @staticmethod
    def update_user_balance(username: str, amount: float) -> bool:
        """Update user balance and save to JSON"""
        user = CGBankDatabase.get_user(username)
        if not user:
            return False
        
        user['balance'] += amount
        return CGBankDatabase._save_data()
    
    @staticmethod
    def request_new_account(account_data: Dict[str, Any]) -> bool:
        """Add a new account request to the system"""
        try:
            # Generate a unique request ID
            request_id = str(uuid.uuid4())
            account_data['request_id'] = request_id
            account_data['status'] = 'Pending'
            account_data['request_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Add to account requests
            BANK_DATA['account_requests'].append(account_data)
            
            # Save to JSON file
            return CGBankDatabase._save_data()
        except Exception as e:
            print(f"Error saving account request: {e}")
            return False

class RexaBot:
    """CGBank's intelligent banking assistant with enhanced NLP capabilities"""
    
    def __init__(self):
        self.name = "Rexa"
        self.service_keywords = {
            'balance_inquiry': ['balance', 'account balance', 'how much money', 'check balance', 
                              'current balance', 'what do i have', 'funds available', 'available balance',
                              'remaining balance', 'account summary'],
            'transaction_history': ['transaction', 'history', 'statement', 'recent transactions', 
                                  'last transactions', 'past payments', 'my spending', 'past expenses',
                                  'payment history', 'transaction details', 'transaction summary'],
            'fund_transfer': ['transfer', 'send money', 'transfer money', 'transfer funds', 
                            'move money', 'pay someone', 'send to friend', 'wire transfer',
                            'remit', 'send cash'],
            'bill_payment': ['pay bill', 'bill payment', 'utility bill', 'electricity bill', 
                           'water bill', 'gas bill', 'phone bill', 'internet bill',
                           'credit card bill', 'mobile recharge'],
            'bank_info': ['about cgbank', 'bank information', 'bank details', 'what is cgbank', 
                         'bank services', 'products offered', 'bank features', 'branch locations',
                         'contact bank', 'bank timings'],
            'loan_info': ['loan', 'borrow', 'credit', 'home loan', 'personal loan', 'car loan',
                         'education loan', 'interest rates', 'eligibility', 'how to apply',
                         'mortgage', 'vehicle loan', 'student loan'],
            'scheme_info': ['modi scheme', 'pm farmer scheme', 'thangamagal scheme', 'government scheme',
                          'scheme details', 'scheme information', 'subsidy', 'farmer benefits',
                          'women benefits', 'agricultural scheme'],
            'account_info': ['account', 'account type', 'student account', 'nri account', 'senior account', 
                            'how to open new acc', 'account types', 'new account', 'create account', 
                            'open account', 'account opening', 'how to create account'],
            'monthly_report': ['monthly report', 'monthly statement', 'monthly summary', 
                             'monthly transactions', 'monthly spending', 'monthly analysis','account statement'
                             'report for month', 'statement for month']
        }
        
        self.knowledge_base = self._create_knowledge_base()
    
    def _create_knowledge_base(self) -> Dict[str, Any]:
        """Create a structured knowledge base from the JSON data"""
        kb = {
            'bank': CGBankDatabase.get_bank_info(),
            'loans': CGBankDatabase.get_loan_products(),
            'schemes': CGBankDatabase.get_government_schemes(),
            'accounts': CGBankDatabase.get_account_info(),
            'services': CGBankDatabase.get_bank_info().get('services', []),
            'branches': CGBankDatabase.get_bank_info().get('branches', [])
        }
        return kb
    
    def _get_random_response(self, response_type: str) -> str:
        """Get a random response of a given type"""
        return random.choice(BANK_DATA['bot_responses'].get(response_type, ["I'm here to help."]))
    
    def _extract_loan_info(self, loan_type: str) -> str:
        """Enhanced loan info extraction with fuzzy matching"""
        loans = CGBankDatabase.get_loan_products()
        
        for key, loan_data in loans.items():
            if loan_type.lower() in loan_data['name'].lower():
                return self._format_loan_response(loan_data)
        
        loan_names = [loan['name'].lower() for loan in loans.values()]
        matches = get_close_matches(loan_type.lower(), loan_names, n=1, cutoff=0.6)
        
        if matches:
            matched_loan_name = matches[0]
            for loan_data in loans.values():
                if loan_data['name'].lower() == matched_loan_name:
                    return self._format_loan_response(loan_data)
        
        return self._get_all_loans_info()
    
    def _format_loan_response(self, loan_data: Dict[str, Any]) -> str:
        """Format loan information into a response"""
        return (f"**{loan_data['name']}**\n"
               f"- Amount: {loan_data['amount']}\n"
               f"- Interest Rate: {loan_data['interest']}\n"
               f"- Tenure: {loan_data['tenure']}\n\n"
               f"Visit any CGBank branch to apply!")
    
    def _get_all_loans_info(self) -> str:
        """Get information about all loan products"""
        loans = CGBankDatabase.get_loan_products()
        response = "**Loan Products at CGBank:**\n\n"
        for loan in loans.values():
            response += (f"**{loan['name']}**\n"
                        f"- Amount: {loan['amount']}\n"
                        f"- Interest: {loan['interest']}\n"
                        f"- Tenure: {loan['tenure']}\n\n")
        return response
    
    def _extract_scheme_info(self, scheme_name: str) -> str:
        """Enhanced scheme info extraction with fuzzy matching"""
        schemes = CGBankDatabase.get_government_schemes()
        
        for key, scheme_data in schemes.items():
            if scheme_name.lower() in scheme_data['name'].lower():
                return self._format_scheme_response(scheme_data)
        
        scheme_names = [scheme['name'].lower() for scheme in schemes.values()]
        matches = get_close_matches(scheme_name.lower(), scheme_names, n=1, cutoff=0.6)
        
        if matches:
            matched_scheme_name = matches[0]
            for scheme_data in schemes.values():
                if scheme_data['name'].lower() == matched_scheme_name:
                    return self._format_scheme_response(scheme_data)
        
        return self._get_all_schemes_info()
    
    def _format_scheme_response(self, scheme_data: Dict[str, Any]) -> str:
        """Format scheme information into a response"""
        benefits = "\n".join([f"- {benefit}" for benefit in scheme_data['benefits']])
        return (f"**{scheme_data['name']}**\n\n"
               f"**Benefits:**\n{benefits}\n\n"
               f"**Eligibility:** {scheme_data['eligibility']}\n\n"
               f"**How to Apply:** {scheme_data['application']}")
    
    def _get_all_schemes_info(self) -> str:
        """Get information about all government schemes"""
        schemes = CGBankDatabase.get_government_schemes()
        response = "**Government Schemes at CGBank:**\n\n"
        for scheme in schemes.values():
            response += f"**{scheme['name']}**\n"
            response += f"- Eligibility: {scheme['eligibility']}\n\n"
        return response
    
    def _extract_account_info(self, account_type: str) -> str:
        """Enhanced account info extraction with fuzzy matching"""
        accounts = CGBankDatabase.get_account_info()
        
        # First try exact match with account keys
        for key, account_data in accounts.items():
            if account_type.lower() == key.lower():
                return self._format_account_response(account_data)
        
        # Then try matching with account names
        for account_data in accounts.values():
            if account_type.lower() in account_data.get('name', '').lower():
                return self._format_account_response(account_data)
        
        # Finally try fuzzy matching
        account_names = [account_data.get('name', '').lower() for account_data in accounts.values()]
        matches = get_close_matches(account_type.lower(), account_names, n=1, cutoff=0.6)
        
        if matches:
            matched_account_name = matches[0]
            for account_data in accounts.values():
                if account_data.get('name', '').lower() == matched_account_name:
                    return self._format_account_response(account_data)
        
        return self._get_all_accounts_info()
    
    def _get_account_creation_info(self) -> str:
        """Provide detailed information about account creation process"""
        accounts = CGBankDatabase.get_account_info()
        response = "**Account Opening Process at CGBank:**\n\n"
        response += "To open a new account with CGBank, please follow these steps:\n\n"
        response += "1. Aadhar card xerox or any other government ID proof\n\n"
        response += "2. Passport size photo\n\n"
        response += "3. Min deposit amount ₹500\n\n"    
        response += "Contact our nearest branch to create a new bank account \n\n"    
        return response

    def _format_account_response(self, account_data: Dict[str, Any]) -> str:
        """Format account information into a response with proper field checking"""
        try:
            name = account_data.get('name', 'Account')
            features = account_data.get('features', 'No special features')
            min_balance = account_data.get('min_balance', 0)
            interest_rate = account_data.get('interest_rate', 0)
            documents = account_data.get('documents', 'Not specified')
            
            return (f"**{name}**\n\n"
                   f"**Features:**\n{features}\n\n"
                   f"**Minimum Balance:** ₹{min_balance:,.2f}\n"
                   f"**Interest Rate:** {interest_rate}%\n"
                   f"**Required Documents:** {documents}\n\n"
                   f"Visit any CGBank branch to open this account!")
        except Exception as e:
            print(f"Error formatting account response: {e}")
            return "I'm having trouble retrieving the account details. Please try again later."
    
    def _get_all_accounts_info(self) -> str:
        """Get information about all account types"""
        accounts = CGBankDatabase.get_account_info()
        response = "**Account Types at CGBank:**\n\n"
        for account_type, account_data in accounts.items():
            name = account_data.get('name', account_type.replace('_', ' ').title())
            min_balance = account_data.get('min_balance', 0)
            interest_rate = account_data.get('interest_rate', 0)
            
            response += (f"**{name}**\n"
                        f"- Min Balance: ₹{min_balance:,.2f}\n"
                        f"- Interest: {interest_rate}%\n\n")
        response += "\nYou can ask me about specific accounts like 'student account', 'NRI account', or 'senior account' for more details."
        return response
    
    def _generate_monthly_report(self, username: str) -> Dict[str, Any]:
        """Generate a monthly report for the user"""
        transactions = CGBankDatabase.get_user_transactions(username)
        if not transactions:
            return None
        
        df = pd.DataFrame(transactions)
        last_month = datetime.now() - timedelta(days=30)
        df_last_month = df[df['date'] >= last_month]
        
        if df_last_month.empty:
            return None
        
        total_credit = df_last_month[df_last_month['amount'] > 0]['amount'].sum()
        total_debit = abs(df_last_month[df_last_month['amount'] < 0]['amount'].sum())
        net_change = total_credit - total_debit
        
        report = {
            'start_date': last_month.strftime('%Y-%m-%d'),
            'end_date': datetime.now().strftime('%Y-%m-%d'),
            'total_transactions': len(df_last_month),
            'total_credit': total_credit,
            'total_debit': total_debit,
            'net_change': net_change,
            'transactions': df_last_month.to_dict('records')
        }
        
        return report
    
    def _create_pdf_report(self, username: str, report_data: Dict[str, Any]) -> BytesIO:
        """Create a PDF report with transaction details and user information"""
        user_data = CGBankDatabase.get_user(username)
        if not user_data:
            return None
        
        try:
            pdf_buffer = PDFGenerator.generate_pdf_report(user_data, report_data)
            return pdf_buffer
        except Exception as e:
            print(f"Error generating PDF report: {e}")
            return None
    
    def _create_download_link(self, pdf_buffer: BytesIO, username: str) -> str:
        """Create a download link for the PDF report"""
        try:
            b64 = base64.b64encode(pdf_buffer.getvalue()).decode()
            filename = f"CGBank_Statement_{username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            href = f'<a href="data:application/pdf;base64,{b64}" download="{filename}">Download PDF Report</a>'
            return href
        except Exception as e:
            print(f"Error creating download link: {e}")
            return "Error generating download link"
    
    def _get_ollama_response(self, message: str, context: str = "") -> str:
        """Get a response from Ollama LLM with banking context"""
        try:
            prompt = f"""
            You are Rexa, an AI banking assistant for CGBank. Provide helpful, accurate responses 
            to customer queries about banking services. Use the following context when relevant:
            
            {context}
            
            Knowledge Base:
            {json.dumps(self.knowledge_base, indent=2)}
            
            Customer Query: {message}
            
            Guidelines:
            1. Be polite and professional
            2. Provide accurate information from the knowledge base
            3. If unsure, ask for clarification
            4. Keep responses concise but helpful
            5. For account-specific queries, verify user is logged in
            
            Response:
            """
            
            response = ollama.generate(
                model='banking-assistant',
                prompt=prompt,
                options={
                    'temperature': 0.7,
                    'max_tokens': 200,
                    'top_p': 0.9
                }
            )
            
            return response['choices'][0]['text'].strip()
        except Exception as e:
            print(f"Error getting Ollama response: {e}")
            return "I'm having trouble processing your request. Please try again later."
    
    def _identify_intent(self, message: str) -> Optional[str]:
        """Identify the intent of the user message using NLP techniques"""
        message = message.lower()
        
        for intent, keywords in self.service_keywords.items():
            if any(re.search(r'\b' + re.escape(keyword) + r'\b', message) for keyword in keywords):
                return intent
        
        all_keywords = [kw for sublist in self.service_keywords.values() for kw in sublist]
        matches = get_close_matches(message, all_keywords, n=1, cutoff=0.6)
        
        if matches:
            matched_keyword = matches[0]
            for intent, keywords in self.service_keywords.items():
                if matched_keyword in keywords:
                    return intent
        
        return None
    
    def process_message(self, message: str, username: Optional[str] = None) -> str:
        """Process a user message with enhanced NLP and return an appropriate response"""
        message = message.lower()
        user_data = CGBankDatabase.get_user(username) if username else None
        intent = self._identify_intent(message)
        
        if any(word in message for word in ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening']):
            if user_data:
                return f"Hello {user_data['name']}! {self._get_random_response('greetings')}"
            return self._get_random_response('greetings')
        
        if any(word in message for word in ['thank', 'thanks', 'appreciate']):
            return self._get_random_response('thanks')
        
        if intent == 'monthly_report':
            if not user_data:
                return "Please log in to view your monthly report."
            
            report = self._generate_monthly_report(username)
            if not report:
                return "You don't have any transactions in the last month to generate a report."
            
            # Generate PDF report
            pdf_buffer = self._create_pdf_report(username, report)
            if pdf_buffer:
                # Store the download link in session state
                download_link = self._create_download_link(pdf_buffer, username)
                st.session_state.download_link = download_link
                
                response = (f"**📊 Monthly Report ({report['start_date']} to {report['end_date']})**\n\n"
                          f"**Total Transactions:** {report['total_transactions']}\n"
                          f"**Total Credit:** ₹{report['total_credit']:,.2f}\n"
                          f"**Total Debit:** ₹{report['total_debit']:,.2f}\n"
                          f"**Net Change:** ₹{report['net_change']:,.2f}\n\n"
                          "Your PDF report is ready! Would you like to download it now? (Yes/No)")
            else:
                response = "I couldn't generate the PDF report. Please try again later."
            
            return response
        
        if message.lower() in ['yes', 'y', 'download', 'download report'] and 'download_link' in st.session_state:
            download_link = st.session_state.download_link
            del st.session_state.download_link
            return f"Here's your download link:\n\n{download_link}"
        
        if message.lower() in ['no', 'n', 'cancel'] and 'download_link' in st.session_state:
            del st.session_state.download_link
            return "Monthly report download cancelled. Let me know if you need anything else!"
        
        if intent == 'balance_inquiry':
            if user_data:
                return self._get_random_response('balance_inquiry').format(balance=user_data['balance'])
            return "Please log in to check your account balance."
        
        elif intent == 'transaction_history':
            if user_data:
                # Get transactions from session state or database
                transactions = CGBankDatabase.get_user_transactions(username)[:5]
                if not transactions:
                    return "You don't have any transactions yet."
                
                response = "Here are your recent transactions:\n\n"
                for i, txn in enumerate(transactions, 1):
                    sign = "+" if txn['amount'] > 0 else ""
                    response += (f"{i}. {txn['description']}\n"
                                f"   Amount: {sign}₹{txn['amount']:,.2f}\n"
                                f"   Date: {txn['date'].strftime('%Y-%m-%d %H:%M')}\n"
                                f"   Balance: ₹{txn['balance']:,.2f}\n\n")
                return response
            return "Please log in to view your transaction history."
        
        elif intent == 'fund_transfer':
            if user_data:
                return self._get_random_response('fund_transfer')
            return "Please log in to initiate a fund transfer."
        
        elif intent == 'bill_payment':
            if user_data:
                return self._get_random_response('bill_payment')
            return "Please log in to pay your bills."
        
        elif intent == 'bank_info':
            bank_info = CGBankDatabase.get_bank_info()
            if 'branch' in message or 'location' in message:
                branches = "\n".join([f"- {branch['name']}: {branch['address']}" 
                                    for branch in bank_info['branches']])
                return f"**CGBank Branches:**\n{branches}"
            elif 'service' in message or 'product' in message:
                services = "\n".join([f"- {service}" for service in bank_info['services']])
                return f"**CGBank Services:**\n{services}"
            elif 'time' in message or 'hour' in message:
                timings = bank_info['branches'][0]['timings']
                return f"**Branch Timings:**\n{timings}"
            else:
                return (f"**About {bank_info['name']}:**\n"
                       f"{bank_info['tagline']}\n\n"
                       f"**Address:** {bank_info['address']}\n"
                       f"**Contact:** {bank_info['contact']}\n"
                       f"**Email:** {bank_info['email']}\n"
                       f"**Helpline:** {bank_info['helpline']}")
        
        elif intent == 'loan_info':
            if 'personal' in message:
                return self._extract_loan_info('Personal Loan')
            elif 'home' in message:
                return self._extract_loan_info('Home Loan')
            elif 'car' in message or 'auto' in message:
                return self._extract_loan_info('Car Loan')
            elif 'education' in message:
                return self._extract_loan_info('Education Loan')
            else:
                return self._get_all_loans_info()
        
        elif intent == 'account_info':
            if any(word in message for word in ['create', 'open', 'new']):
                return self._get_account_creation_info()
            elif 'student' in message:
                return self._extract_account_info('student_account')
            elif 'nri' in message:
                return self._extract_account_info('nri_account')   
            elif 'senior' in message:
                return self._extract_account_info('senior_account')
            else:
                return self._get_all_accounts_info()
            
        elif intent == 'scheme_info':
            if 'modi' in message:
                return self._extract_scheme_info('Modi Scheme')
            elif 'farmer' in message:
                return self._extract_scheme_info('PM Farmer Scheme')
            elif 'thangamagal' in message or 'women' in message:
                return self._extract_scheme_info('Thangamagal Scheme')
            else:
                return self._get_all_schemes_info()
            
        context = ""
        if user_data:
            context = f"Customer: {user_data['name']}, Account Balance: ₹{user_data['balance']:,.2f}"
        
        return self._get_ollama_response(message, context)

class CGBankApp:
    """Streamlit application for CGBank"""
    
    def __init__(self):
        self.bot = RexaBot()
        self.feedback_system = FeedbackSystem()
        self._initialize_session_state()
        self._setup_page_config()
        self._load_custom_styles()
    
    def _initialize_session_state(self):
        """Initialize session state variables"""
        if 'logged_in' not in st.session_state:
            st.session_state.logged_in = False
        if 'current_user' not in st.session_state:
            st.session_state.current_user = None
        if 'page' not in st.session_state:
            st.session_state.page = "login"
        if 'bot_conversation' not in st.session_state:
            st.session_state.bot_conversation = []
        if 'show_popup_bot' not in st.session_state:
            st.session_state.show_popup_bot = False
        if 'transactions' not in st.session_state:
            st.session_state.transactions = []
        if 'download_link' not in st.session_state:
            st.session_state.download_link = None
        if 'feedback_submitted' not in st.session_state:
            st.session_state.feedback_submitted = False
        if 'show_create_account' not in st.session_state:
            st.session_state.show_create_account = False
    
    def _setup_page_config(self):
        """Configure the Streamlit page settings"""
        st.set_page_config(
            page_title="CGBank - Coimbatore Trusted Banking Partner",
            page_icon="🏦",
            layout="wide",
            initial_sidebar_state="expanded"
        )
    
    def _load_custom_styles(self):
        """Load custom CSS styles"""
        st.markdown("""
        <style>
            .main-header {
                background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
                padding: 2rem;
                border-radius: 10px;
                color: white;
                text-align: center;
                margin-bottom: 2rem;
            }
            .account-card {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 1.5rem;
                border-radius: 10px;
                color: white;
                margin: 1rem 0;
            }
            .bot-message {
                background: #f8f9fa;
                padding: 1rem;
                border-radius: 10px;
                margin: 0.5rem 0;
                color: #333;
                border-left: 4px solid #2a5298;
            }
            .user-message {
                background: #e3f2fd;
                padding: 1rem;
                border-radius: 10px;
                margin: 0.5rem 0;
                color: #333;
                border-left: 4px solid #1976d2;
            }
            .popup-bot {
                position: fixed;
                bottom: 20px;
                right: 20px;
                width: 350px;
                background: white;
                border-radius: 10px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.2);
                z-index: 1000;
            }
            .popup-bot-header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 1rem;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
            .transaction-item {
                background: white;
                padding: 1rem;
                border-radius: 8px;
                margin: 0.5rem 0;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .popup-user-message {
                background: #e3f2fd;
                padding: 8px 12px;
                border-radius: 8px;
                margin: 8px 0;
                margin-left: auto;
                max-width: 80%;
            }
            .popup-bot-message {
                background: #f8f9fa;
                padding: 8px 12px;
                border-radius: 8px;
                margin: 8px 0;
                max-width: 80%;
            }
            .popup-toggle-btn {
                position: fixed;
                bottom: 20px;
                right: 20px;
                z-index: 1001;
                width: 80px;
                height: 80px;
                border-radius: 50%;
                background: transparent;
                border: none;
                cursor: pointer;
                padding: 0;
                margin: 0;
            }
            .popup-toggle-btn img {
                width: 100%;
                height: 100%;
                object-fit: contain;
                border-radius: 50%;
                transition: transform 0.3s ease;
            }
            .popup-toggle-btn img:hover {
                transform: scale(1.1);
            }
            .quick-action-btn {
                margin: 0.2rem 0;
                width: 100%;
            }
            .report-card {
                background: white;
                padding: 1.5rem;
                border-radius: 10px;
                margin: 1rem 0;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }
            .feedback-form {
                background: white;
                padding: 1.5rem;
                border-radius: 10px;
                margin: 1rem 0;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }
            .star-rating {
                display: flex;
                justify-content: center;
                margin: 1rem 0;
            }
            .star-rating input {
                display: none;
            }
            .star-rating label {
                font-size: 2rem;
                color: #ddd;
                cursor: pointer;
                margin: 0 0.2rem;
            }
            .star-rating input:checked ~ label {
                color: #ffc107;
            }
            .star-rating label:hover,
            .star-rating label:hover ~ label {
                color: #ffc107;
            }
            .create-account-form {
                background: white;
                padding: 2rem;
                border-radius: 10px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                margin-top: 2rem;
            }
        </style>
        """, unsafe_allow_html=True)
    
    def _render_feedback_form(self):
        """Render the feedback form in the dashboard"""
        with st.expander("📝 Give Us Feedback"):
            with st.form("feedback_form", clear_on_submit=True):
                st.markdown("### We Value Your Feedback")
                
                # Name input
                name = st.text_input("Your Name", placeholder="Enter your name")
                
                # Email input
                email = st.text_input("Your Email", placeholder="Enter your email")
                
                # Star rating
                st.markdown("### Rate Your Experience")
                rating = st.slider("Rating", 1, 5, 5, key="feedback_rating")
                
                # Feedback text
                feedback = st.text_area("Your Feedback", placeholder="Share your experience with us...", height=150)
                
                # Submit button
                submitted = st.form_submit_button("Submit Feedback", use_container_width=True)
                
                if submitted:
                    if not name or not feedback:
                        st.error("Please provide both your name and feedback!")
                        return
                    
                    # Send feedback email
                    success = self.feedback_system.send_feedback_email(
                        name=name,
                        email=email if email else "Not provided",
                        rating=rating,
                        feedback=feedback
                    )
                    
                    if success:
                        st.success("Thank you for your feedback! We appreciate your time.")
                        st.session_state.feedback_submitted = True
                    else:
                        st.error("Failed to submit feedback. Please try again later.")
    
    def _render_login_page(self):
        """Render the login page with account creation option"""
        st.markdown("""
        <div class="main-header">
            <h1>🏦 CGBank</h1>
            <h3>Coimbatore Trusted Banking Partner</h3>
            <h4>Secure • Reliable • Innovative</h4>
            <p>174/2 Avinasi road,Annai statue,Coimbatore-641029</p>
            <p>Contact:+91-63820-74060</p>
            <p>Email:Cgbankcbe@gmail.com</p>
            <h5>Welcome to CGBank! Your trusted partner in banking services.</h5> 
            <p>HELPLINE:1800-123-4506</p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            if st.session_state.show_create_account:
                self._render_create_account_form()
            else:
                self._render_login_form()
    
    def _render_login_form(self):
        """Render the login form"""
        st.markdown("### Login to Your Account")
        
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            
            col1, col2 = st.columns(2)
            with col1:
                submitted = st.form_submit_button("Login", use_container_width=True)
            with col2:
                create_account = st.form_submit_button("Create New Account", use_container_width=True)
            
            if submitted:
                if not username or not password:
                    st.error("Please enter both username and password!")
                    return
                
                try:
                    if not CGBankDatabase.verify_user(username, password):
                        st.error("Invalid username or password!")
                        return
                        
                    st.session_state.logged_in = True
                    st.session_state.current_user = username.lower()
                    st.session_state.page = "dashboard"
                    st.session_state.transactions = CGBankDatabase.get_user_transactions(username)
                    st.success("Login successful!")
                    st.rerun()
                    st.balloons()
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")
            
            if create_account:
                st.session_state.show_create_account = True
                st.rerun()
    
    def _render_create_account_form(self):
        """Render the account creation form"""
        st.markdown("### Create a New CGBank Account")
        
        with st.form("create_account_form"):
            st.markdown("#### Personal Information")
            full_name = st.text_input("Full Name", placeholder="Enter your full name")
            email = st.text_input("Email Address", placeholder="Enter your email address")
            phone = st.text_input("Phone Number", placeholder="Enter your phone number")
            address = st.text_area("Residential Address", placeholder="Enter your full address")
            
            st.markdown("#### Account Details")
            account_type = st.selectbox(
                "Account Type",
                options=["Student Account", "NRI Account", "Senior Citizen Account", "Regular Savings Account"],
                index=0
            )
            
            username = st.text_input("Choose Username", placeholder="Create a username")
            password = st.text_input("Create Password", type="password", placeholder="Create a password")
            confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm your password")
            
            st.markdown("#### KYC Information")
            aadhar_number = st.text_input("Aadhar Number", placeholder="Enter 12-digit Aadhar number")
            pan_number = st.text_input("PAN Number", placeholder="Enter PAN number").upper()
            
            col1, col2 = st.columns(2)
            with col1:
                submit = st.form_submit_button("Submit Application", use_container_width=True)
            with col2:
                cancel = st.form_submit_button("Cancel", use_container_width=True)
            
            if cancel:
                st.session_state.show_create_account = False
                st.rerun()
            
            if submit:
                if not all([full_name, email, phone, address, username, password, aadhar_number, pan_number]):
                    st.error("Please fill in all required fields!")
                    return
                
                if password != confirm_password:
                    st.error("Passwords do not match!")
                    return
                
                if len(aadhar_number) != 12 or not aadhar_number.isdigit():
                    st.error("Please enter a valid 12-digit Aadhar number!")
                    return
                
                if len(pan_number) != 10 or not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]$', pan_number):
                    st.error("Please enter a valid PAN number!")
                    return
                
                # Check if username already exists
                if CGBankDatabase.get_user(username):
                    st.error("Username already exists! Please choose another one.")
                    return
                
                # Prepare account data
                account_data = {
                    "full_name": full_name,
                    "email": email,
                    "phone": phone,
                    "address": address,
                    "account_type": account_type,
                    "username": username,
                    "password": CGBankDatabase.hash_password(password),
                    "aadhar_number": aadhar_number,
                    "pan_number": pan_number,
                    "request_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                # Save account request
                if CGBankDatabase.request_new_account(account_data):
                    st.session_state.show_create_account = False
                    st.success("""
                    Your account request has been submitted successfully!
                    
                    Our bank staff will contact you shortly to complete the KYC process.
                    You'll receive your account details via email once approved.
                    
                    Thank you for choosing CGBank!
                    """)
                else:
                    st.error("Failed to submit account request. Please try again later.")
    
    def _render_dashboard(self):
        """Render the dashboard page"""
        user = CGBankDatabase.get_user(st.session_state.current_user)
        if not user:
            st.error("User not found!")
            st.session_state.logged_in = False
            st.session_state.current_user = None
            st.session_state.page = "login"
            st.rerun()
            return
        
        st.markdown(f"""
        <div class="main-header">
            <h1>Welcome back, {user['name']}! 👋</h1>
            <p>Account: {user['account_number']} | {user['account_type']} Account</p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"""
            <div class="account-card">
                <h3>💰 Account Balance</h3>
                <h2>₹{user['balance']:,.2f}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class="account-card">
                <h3>📊 This Month</h3>
                <h2>₹2,340.50</h2>
                <p>↑ +12.5%</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("### ⚡ Quick Actions")
        cols = st.columns(5)
        with cols[0]:
            if st.button("💸 Transfer Money", key="dashboard_transfer", use_container_width=True):
                st.session_state.page = "transfer"
                st.rerun()
        with cols[1]:
            if st.button("💰 Pay Bills", key="dashboard_bills", use_container_width=True):
                st.session_state.page = "bills"
                st.rerun()
        with cols[2]:
            if st.button("📊 Transactions", key="dashboard_transactions", use_container_width=True):
                st.session_state.page = "transactions"
                st.rerun()
        with cols[3]:
            if st.button("📈 Reports", key="dashboard_reports", use_container_width=True):
                st.session_state.page = "reports"
                st.rerun()
        with cols[4]:
            if st.button("🤖 Chat with Rexa", key="dashboard_rexa", use_container_width=True):
                st.session_state.page = "rexa"
                st.rerun()
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 📈 Spending Overview")
            categories = CGBankDatabase.get_spending_categories(st.session_state.current_user)
            df = pd.DataFrame(categories)
            fig = px.pie(df, values='amount', names='name', title="Monthly Spending by Category")
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("### 📅 Upcoming Bills")
            bills = CGBankDatabase.get_user_bills(st.session_state.current_user)
            for bill in bills[:3]:
                status_color = "#ffc107" if bill["status"] == "Due Soon" else "#28a745"
                st.markdown(f"""
                <div class="transaction-item">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <h4 style="margin: 0;">{bill['name']}</h4>
                            <p style="margin: 0; color: #6c757d;">Due: {bill['due']}</p>
                        </div>
                        <div style="text-align: right;">
                            <h4 style="margin: 0; color: #dc3545;">₹{bill['amount']:,.2f}</h4>
                            <span style="color: {status_color}; font-size: 0.8em;">{bill['status']}</span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        # Add feedback form to dashboard
        self._render_feedback_form()
    
    def _render_report_page(self):
        """Render the report analysis page"""
        st.markdown("### 📊 Statement Analysis Report")
        
        if not st.session_state.transactions:
            st.session_state.transactions = CGBankDatabase.get_user_transactions(st.session_state.current_user)
        
        df = pd.DataFrame(st.session_state.transactions)
        
        if df.empty or 'date' not in df.columns:
            st.warning("No transaction data available for analysis")
            return
        
        min_date = df['date'].min().date()
        max_date = df['date'].max().date()
        default_start = max(min_date, max_date - timedelta(days=30))
        default_end = max_date
        
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", 
                                     value=default_start,
                                     min_value=min_date,
                                     max_value=max_date)
        with col2:
            end_date = st.date_input("End Date", 
                                   value=default_end,
                                   min_value=min_date,
                                   max_value=max_date)
        
        mask = (df['date'].dt.date >= start_date) & (df['date'].dt.date <= end_date)
        filtered_df = df.loc[mask]
        
        if filtered_df.empty:
            st.warning("No transactions found for the selected date range")
            return
        
        st.markdown("#### 📋 Summary Statistics")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f"""
            <div class="report-card">
                <h4>Total Transactions</h4>
                <h2>{len(filtered_df)}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            total_credit = filtered_df[filtered_df['amount'] > 0]['amount'].sum()
            st.markdown(f"""
            <div class="report-card">
                <h4>Total Credit</h4>
                <h2>₹{total_credit:,.2f}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            total_debit = abs(filtered_df[filtered_df['amount'] < 0]['amount'].sum())
            st.markdown(f"""
            <div class="report-card">
                <h4>Total Debit</h4>
                <h2>₹{total_debit:,.2f}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("#### 📈 Transaction Trends")
        daily_trends = filtered_df.set_index('date').resample('D')['amount'].sum().reset_index()
        fig = px.line(daily_trends, x='date', y='amount', 
                     title="Daily Transaction Amounts",
                     labels={'amount': 'Amount (₹)', 'date': 'Date'})
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("#### 🗂️ Transaction Categories")
        filtered_df['category'] = filtered_df['description'].apply(
            lambda x: 'Transfer' if 'transfer' in x.lower() 
            else 'Bill Payment' if 'bill' in x.lower() 
            else 'Salary' if 'salary' in x.lower() 
            else 'Other'
        )
        
        category_df = filtered_df.groupby('category')['amount'].agg(['sum', 'count']).reset_index()
        category_df['sum'] = category_df['sum'].abs()
        
        col1, col2 = st.columns(2)
        with col1:
            fig = px.pie(category_df, values='sum', names='category', 
                        title="Amount by Category")
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = px.bar(category_df, x='category', y='count',
                        title="Number of Transactions by Category")
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("#### 📜 Filtered Transactions")
        filtered_df['date'] = filtered_df['date'].dt.strftime('%Y-%m-%d %H:%M')
        filtered_df['amount'] = filtered_df['amount'].apply(lambda x: f"₹{x:,.2f}")
        st.dataframe(filtered_df[['date', 'description', 'amount']], hide_index=True)
    
    def _render_bot_page(self):
        """Render the chatbot page"""
        st.markdown("""
        <div class="main-header">
            <h1>🤖 Rexa - Your Personal Banking Assistant</h1>
            <p>Ask me anything about your account, transactions, or banking services</p>
        </div>
        """, unsafe_allow_html=True)
        
        for conv in st.session_state.bot_conversation[-10:]:
            if isinstance(conv, dict) and 'user' in conv and 'bot' in conv:
                st.markdown(f"""
                <div class="user-message">
                    <strong>You:</strong> {conv['user']}
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"""
                <div class="bot-message">
                    <strong>🤖 Rexa:</strong> {conv['bot']}
                </div>
                """, unsafe_allow_html=True)
        
        with st.form("chat_form", clear_on_submit=True):
            user_input = st.text_input("Type your message to Rexa:", 
                                     placeholder="Ask me about your account, transactions, or banking services...",
                                     key="chat_input")
            submitted = st.form_submit_button("Send", use_container_width=True)
            
            if submitted and user_input:
                try:
                    bot_response = self.bot.process_message(
                        user_input, 
                        st.session_state.current_user if st.session_state.logged_in else None
                    )
                    
                    st.session_state.bot_conversation.append({
                        'user': user_input,
                        'bot': bot_response
                    })
                    
                    st.rerun()
                except Exception as e:
                    st.error(f"Error processing message: {str(e)}")

    def _render_popup_bot(self):
        """Render the popup bot interface with a GIF toggle button"""
        # Robot GIF URL (you can replace this with your own GIF)
        robot_gif_url = "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExcjVtY2V4bHJ5Z3R0eWJ4c3B6dHh0bHZ5d2V5d3J2dXZ5Z2F4eWZ4ZyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/l0HU7JI8AfUAbM5HO/giphy.gif"
        
        # Create a button with the GIF as its content
        st.markdown(f"""
        <button class="popup-toggle-btn" onclick="document.getElementById('toggle-bot').click()">
            <img src="{robot_gif_url}" alt="Chat with Rexa">
        </button>
        """, unsafe_allow_html=True)
        
        # Hidden checkbox to control the popup state
        show_popup = st.checkbox("Toggle Bot", key="toggle_bot", label_visibility="hidden")
        
        if show_popup:
            st.session_state.show_popup_bot = True
        else:
            st.session_state.show_popup_bot = False
        
        if st.session_state.show_popup_bot:
            st.markdown("""
            <div class="popup-bot">
                <div class="popup-bot-header">
                    <h4 style="margin: 0;">🤖 Rexa - Banking Assistant</h4>
                </div>
                <div style="padding: 1rem; max-height: 300px; overflow-y: auto;">
            """, unsafe_allow_html=True)
            
            for conv in st.session_state.bot_conversation[-5:]:
                if isinstance(conv, dict) and 'user' in conv and 'bot' in conv:
                    st.markdown(f"""
                    <div class="popup-user-message">
                        <strong>You:</strong> {conv['user']}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown(f"""
                    <div class="popup-bot-message">
                        <strong>Rexa:</strong> {conv['bot']}
                    </div>
                    """, unsafe_allow_html=True)
            
            st.markdown("""
                </div>
                <div style="padding: 1rem; border-top: 1px solid #eee;">
                    <p><strong>Quick Banking Commands:</strong></p>
            """, unsafe_allow_html=True)
            
            cols = st.columns(2)
            
            with cols[0]:
                if st.button("💰 Check Balance", key="popup_balance", 
                           help="View your current account balance", 
                           use_container_width=True):
                    self._handle_popup_action("What's my current balance?")
                
                if st.button("📊 Recent Transactions", key="popup_transactions", 
                            help="View your last 5 transactions", 
                            use_container_width=True):
                    self._handle_popup_action("Show my recent transactions")
            
            with cols[1]:
                if st.button("💸 Transfer Money", key="popup_transfer", 
                           help="Initiate a money transfer", 
                           use_container_width=True):
                    self._handle_popup_action("I want to transfer money")
                
                if st.button("🧾 Pay Bills", key="popup_bills", 
                           help="Pay your pending bills", 
                           use_container_width=True):
                    self._handle_popup_action("I want to pay bills")
            
            with st.form("popup_chat_form", clear_on_submit=True):
                user_input = st.text_input("Type your message:", key="popup_input")
                submitted = st.form_submit_button("Send", use_container_width=True)
                
                if submitted and user_input:
                    self._handle_popup_action(user_input)
            
            st.markdown("</div>", unsafe_allow_html=True)
    
    def _handle_popup_action(self, message: str):
        """Handle an action from the popup bot"""
        try:
            bot_response = self.bot.process_message(
                message, 
                st.session_state.current_user if st.session_state.logged_in else None
            )
            
            st.session_state.bot_conversation.append({
                'user': message,
                'bot': bot_response
            })
            
            st.rerun()
        except Exception as e:
            st.error(f"Error handling popup action: {str(e)}")
    
    def _render_sidebar(self):
        """Render the sidebar navigation"""
        with st.sidebar:
            st.markdown("### 🏦 CGBank Navigation")
            
            if st.session_state.logged_in:
                user = CGBankDatabase.get_user(st.session_state.current_user)
                if not user:
                    st.error("User data not found!")
                    return
                
                st.markdown(f"**Welcome, {user['name']}**")
                st.markdown(f"Account: {user['account_number']}")
                
                if st.button("🏠 Dashboard", key="sidebar_dashboard", use_container_width=True):
                    st.session_state.page = "dashboard"
                    st.rerun()
                if st.button("📊 Transactions", key="sidebar_transactions", use_container_width=True):
                    st.session_state.page = "transactions"
                    st.rerun()
                if st.button("💸 Transfer", key="sidebar_transfer", use_container_width=True):
                    st.session_state.page = "transfer"
                    st.rerun()
                if st.button("💰 Bills", key="sidebar_bills", use_container_width=True):
                    st.session_state.page = "bills"
                    st.rerun()
                if st.button("📈 Reports", key="sidebar_reports", use_container_width=True):
                    st.session_state.page = "reports"
                    st.rerun()
                if st.button("🤖 Rexa", key="sidebar_rexa", use_container_width=True):
                    st.session_state.page = "rexa"
                    st.rerun()
                
                st.markdown("---")
                if st.button("🚪 Logout", key="sidebar_logout", use_container_width=True):
                    st.session_state.logged_in = False
                    st.session_state.current_user = None
                    st.session_state.page = "login"
                    st.rerun()
            else:
                st.markdown("Please login to access your account")
    
    def _render_transactions_page(self):
        """Render the transactions page"""
        st.markdown("### 📋 Recent Transactions")
        
        if not st.session_state.transactions:
            st.session_state.transactions = CGBankDatabase.get_user_transactions(st.session_state.current_user)
        
        for txn in st.session_state.transactions[:10]:
            color = "#28a745" if txn['amount'] > 0 else "#dc3545"
            sign = "+" if txn['amount'] > 0 else ""
            
            st.markdown(f"""
            <div class="transaction-item">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <h4 style="margin: 0; color: #2a5298;">{txn['description']}</h4>
                        <p style="margin: 0; color: #6c757d; font-size: 0.9em;">
                            {txn['date'].strftime('%Y-%m-%d %H:%M')}
                        </p>
                    </div>
                    <div style="text-align: right;">
                        <h3 style="margin: 0; color: {color};">{sign}₹{abs(txn['amount']):,.2f}</h3>
                        <p style="margin: 0; color: #6c757d; font-size: 0.9em;">
                            Balance: ₹{txn['balance']:,.2f}
                        </p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    def _render_transfer_page(self):
        """Render the fund transfer page"""
        st.markdown("### 💸 Transfer Money")
        
        user = CGBankDatabase.get_user(st.session_state.current_user)
        if not user:
            st.error("User data not found!")
            return
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Transfer Details")
            with st.form("transfer_form"):
                recipient = st.text_input("Recipient Account", placeholder="Enter account number")
                amount = st.number_input("Amount (₹)", min_value=0.01, step=0.01)
                description = st.text_input("Description (Optional)", placeholder="What's this for?")
                submitted = st.form_submit_button("Transfer", use_container_width=True)
                
                if submitted:
                    try:
                        if amount > 0 and recipient:
                            if amount > user['balance']:
                                st.error("Insufficient funds for this transfer!")
                            else:
                                # Use the database method to ensure JSON is updated
                                success = CGBankDatabase.add_transaction(
                                    st.session_state.current_user,
                                    f'Transfer to {recipient}',
                                    -amount
                                )
                                
                                if success:
                                    st.success(f"Transfer of ₹{amount:,.2f} to {recipient} completed successfully!")
                                    st.balloons()
                                    st.rerun()
                                else:
                                    st.error("Failed to complete transfer. Please try again.")
                        else:
                            st.error("Please enter valid transfer details!")
                    except Exception as e:
                        st.error(f"Error processing transfer: {str(e)}")
        
        with col2:
            st.markdown("#### Recent Recipients")
            recent_recipients = ["cravin (0987654321)", "rahul (1122334455)", "karthik (5566778899)"]
            for recipient in recent_recipients:
                if st.button(f"📤 {recipient}", key=f"recipient_{recipient}", use_container_width=True):
                    st.info(f"Selected: {recipient}")

    def _render_bills_page(self):
        """Render the bills payment page"""
        st.markdown("### 💰 Pay Bills")
        
        user = CGBankDatabase.get_user(st.session_state.current_user)
        if not user:
            st.error("User data not found!")
            return
        
        bills = CGBankDatabase.get_user_bills(st.session_state.current_user)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Upcoming Bills")
            for bill in bills:
                status_color = "#ffc107" if bill["status"] == "Due Soon" else "#28a745"
                st.markdown(f"""
                <div class="transaction-item">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <h4 style="margin: 0;">{bill['name']}</h4>
                            <p style="margin: 0; color: #6c757d;">Due: {bill['due']}</p>
                        </div>
                        <div style="text-align: right;">
                            <h4 style="margin: 0; color: #dc3545;">₹{bill['amount']:,.2f}</h4>
                            <span style="color: {status_color}; font-size: 0.8em;">{bill['status']}</span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"Pay ₹{bill['amount']:,.2f}", key=f"pay_bill_{bill['name']}", use_container_width=True):
                    try:
                        if bill['amount'] > user['balance']:
                            st.error("Insufficient funds to pay this bill!")
                        else:
                            # Use the database method to ensure JSON is updated
                            success = CGBankDatabase.add_bill_payment(
                                st.session_state.current_user,
                                bill['name'],
                                bill['amount']
                            )
                            
                            if success:
                                st.success(f"Payment of ₹{bill['amount']:,.2f} for {bill['name']} processed successfully!")
                                st.balloons()
                                st.rerun()
                            else:
                                st.error("Failed to process payment. Please try again.")
                    except Exception as e:
                        st.error(f"Error processing bill payment: {str(e)}")
        
        with col2:
            st.markdown("#### Pay New Bill")
            with st.form("bill_form"):
                biller = st.selectbox("Select Biller", ["Electricity Company", "Water Department", 
                                                      "Gas Company", "Internet Provider", "Other"])
                if biller == "Other":
                    custom_biller = st.text_input("Enter Biller Name")
                    biller = custom_biller if custom_biller else "Unknown Biller"
                account_num = st.text_input("Account Number")
                bill_amount = st.number_input("Amount (₹)", min_value=0.01, step=0.01)
                submitted = st.form_submit_button("Pay Bill", use_container_width=True)
                
                if submitted and bill_amount > 0:
                    try:
                        if bill_amount > user['balance']:
                            st.error("Insufficient funds to pay this bill!")
                        else:
                            # Create new bill data
                            new_bill = {
                                "name": biller,
                                "amount": bill_amount,
                                "due": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
                                "status": "Upcoming"
                            }
                            
                            # Add the bill and process payment
                            success = CGBankDatabase.add_new_bill(st.session_state.current_user, new_bill)
                            if success:
                                payment_success = CGBankDatabase.add_bill_payment(
                                    st.session_state.current_user,
                                    biller,
                                    bill_amount
                                )
                                
                                if payment_success:
                                    st.success(f"Bill payment of ₹{bill_amount:,.2f} processed successfully!")
                                    st.rerun()
                                else:
                                    st.error("Payment processed but failed to update records.")
                            else:
                                st.error("Failed to add new bill. Please try again.")
                    except Exception as e:
                        st.error(f"Error processing bill payment: {str(e)}")
    
    def run(self):
        """Run the application"""
        self._render_sidebar()
        
        if st.session_state.logged_in:
            self._render_popup_bot()
            
            if st.session_state.page == "dashboard":
                self._render_dashboard()
            elif st.session_state.page == "transactions":
                self._render_transactions_page()
            elif st.session_state.page == "transfer":
                self._render_transfer_page()
            elif st.session_state.page == "bills":
                self._render_bills_page()
            elif st.session_state.page == "reports":
                self._render_report_page()
            elif st.session_state.page == "rexa":
                self._render_bot_page()
        else:
            self._render_login_page()

if __name__ == "__main__":
    app = CGBankApp()
    app.run()