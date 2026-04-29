"""
SMS Notification Service
Sends reminders for upcoming content tasks
"""

from twilio.rest import Client
import os
from datetime import datetime, timedelta

class SMSService:
    def __init__(self):
        self.account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
        self.auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
        self.phone_number = os.environ.get('TWILIO_PHONE_NUMBER')
        
        print(f"DEBUG: SID={self.account_sid[:10] if self.account_sid else 'None'}")
        print(f"DEBUG: Token={'SET' if self.auth_token else 'None'}")
        print(f"DEBUG: Phone={self.phone_number}")
        
        if not all([self.account_sid, self.auth_token, self.phone_number]):
            print("⚠️  Twilio credentials not configured")
            self.client = None
        else:
            self.client = Client(self.account_sid, self.auth_token)
    
    def send_sms(self, to_number, message):
        """Send SMS to user"""
        if not self.client:
            print("❌ Twilio not configured")
            return False
        
        try:
            msg = self.client.messages.create(
                body=message,
                from_=self.phone_number,
                to=to_number
            )
            print(f"✅ SMS sent to {to_number}: {msg.sid}")
            return True
        except Exception as e:
            print(f"❌ SMS failed: {e}")
            return False
    
    def format_batch_reminder(self, tasks):
        """Format multiple upcoming tasks into one message"""
        if not tasks:
            return None
        
        # Group by time
        message = "⏰ Coming up soon:\n"
        for task in tasks[:5]:  # Max 5 tasks to avoid long SMS
            message += f"• {task['time']} {task['platform']} {task['type']}\n"
        
        if len(tasks) > 5:
            message += f"...and {len(tasks) - 5} more"
        
        message += "\nReply STOP to opt out"
        return message
    
    def format_morning_digest(self, tasks_today):
        """Morning overview of the day"""
        if not tasks_today:
            return "✨ All clear today! No posts scheduled."
        
        message = f"📅 Good morning! {len(tasks_today)} tasks today:\n"
        for task in tasks_today[:10]:
            message += f"• {task['time']} {task['platform']} {task['type']}\n"
        
        message += "\nHave a productive day! 🚀"
        return message

sms_service = SMSService()
