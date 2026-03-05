"""
Email notification system for camera alerts.
Supports motion detection, face detection, and other security events.
"""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from typing import Dict, Any, List, Optional, BinaryIO
import time
import os
from datetime import datetime
from homeauto.utils.logging_config import get_logger


class EmailNotifier:
    """Email notification system for camera alerts"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize email notifier with configuration.
        
        Config should include:
        - smtp_server: SMTP server address
        - smtp_port: SMTP port (default: 587 for TLS, 465 for SSL)
        - username: SMTP username
        - password: SMTP password
        - sender_email: Sender email address
        - recipient_emails: List of recipient email addresses
        - use_tls: Use TLS (default: True)
        - use_ssl: Use SSL (default: False)
        """
        self.config = config
        self.logger = get_logger(__name__)
        
        # Default configuration
        self.smtp_server = config.get("smtp_server", "smtp.gmail.com")
        self.smtp_port = config.get("smtp_port", 587)
        self.username = config.get("username", "")
        self.password = config.get("password", "")
        self.sender_email = config.get("sender_email", "")
        self.recipient_emails = config.get("recipient_emails", [])
        self.use_tls = config.get("use_tls", True)
        self.use_ssl = config.get("use_ssl", False)
        
        # Alert configuration
        self.alert_cooldown = config.get("alert_cooldown", 300)  # 5 minutes
        self.last_alert_time: Dict[str, float] = {}
        
        self.logger.info(f"Email notifier initialized for {self.sender_email}")
    
    def _can_send_alert(self, alert_type: str) -> bool:
        """Check if enough time has passed since last alert of this type"""
        current_time = time.time()
        last_time = self.last_alert_time.get(alert_type, 0)
        
        if current_time - last_time >= self.alert_cooldown:
            self.last_alert_time[alert_type] = current_time
            return True
        return False
    
    def _create_email_message(self, 
                             subject: str, 
                             body: str,
                             images: List[BinaryIO] = None) -> MIMEMultipart:
        """Create email message with optional images"""
        message = MIMEMultipart("related")
        message["From"] = self.sender_email
        message["To"] = ", ".join(self.recipient_emails)
        message["Subject"] = subject
        
        # Create alternative part for HTML and plain text
        alternative = MIMEMultipart("alternative")
        message.attach(alternative)
        
        # Plain text version
        text_part = MIMEText(body, "plain")
        alternative.attach(text_part)
        
        # HTML version
        html_body = f"""
        <html>
        <body>
            <h2>Home Automation Security Alert</h2>
            <p><strong>Subject:</strong> {subject}</p>
            <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid #dc3545;">
                {body.replace('\n', '<br>')}
            </div>
        """
        
        if images:
            html_body += "<h3>Detection Images:</h3>"
            for i, image_data in enumerate(images):
                # For now, we'll reference images as attachments
                html_body += f'<p>Image {i+1} attached</p>'
        
        html_body += """
            <hr>
            <p style="color: #6c757d; font-size: 12px;">
                This is an automated alert from your Home Automation System.
            </p>
        </body>
        </html>
        """
        
        html_part = MIMEText(html_body, "html")
        alternative.attach(html_part)
        
        # Attach images
        if images:
            for i, image_data in enumerate(images):
                image_part = MIMEImage(image_data.read())
                image_part.add_header("Content-ID", f"<image{i}>")
                image_part.add_header("Content-Disposition", "attachment", filename=f"detection_{i}.jpg")
                message.attach(image_part)
        
        return message
    
    def send_email(self, 
                  subject: str, 
                  body: str,
                  images: List[BinaryIO] = None) -> bool:
        """Send email with given subject and body"""
        if not self.recipient_emails:
            self.logger.warning("No recipient emails configured")
            return False
        
        try:
            # Create message
            message = self._create_email_message(subject, body, images)
            
            # Connect to SMTP server
            if self.use_ssl:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, context=context) as server:
                    server.login(self.username, self.password)
                    server.send_message(message)
            else:
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    if self.use_tls:
                        server.starttls()
                    server.login(self.username, self.password)
                    server.send_message(message)
            
            self.logger.info(f"Email sent successfully: {subject}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send email: {e}")
            return False
    
    def send_motion_alert(self, 
                         camera_name: str,
                         camera_ip: str,
                         confidence: float,
                         image_data: BinaryIO = None) -> bool:
        """Send motion detection alert"""
        alert_type = f"motion_{camera_ip}"
        
        if not self._can_send_alert(alert_type):
            self.logger.debug(f"Alert cooldown active for {alert_type}")
            return False
        
        subject = f"🚨 Motion Detected - {camera_name}"
        body = f"""
        Motion has been detected on camera: {camera_name}
        
        Details:
        - Camera: {camera_name}
        - IP Address: {camera_ip}
        - Confidence: {confidence:.1%}
        - Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        - Location: Home
        
        Please check the camera feed for more details.
        """
        
        images = [image_data] if image_data else None
        return self.send_email(subject, body, images)
    
    def send_face_alert(self,
                       camera_name: str,
                       camera_ip: str,
                       confidence: float,
                       face_count: int,
                       recognized_faces: List[str] = None,
                       image_data: BinaryIO = None) -> bool:
        """Send face detection alert"""
        alert_type = f"face_{camera_ip}"
        
        if not self._can_send_alert(alert_type):
            self.logger.debug(f"Alert cooldown active for {alert_type}")
            return False
        
        # Determine alert level
        if recognized_faces:
            alert_level = "👤 Recognized"
            face_info = f"Recognized: {', '.join(recognized_faces)}"
        else:
            alert_level = "⚠️ Unknown"
            face_info = "Unknown person(s) detected"
        
        subject = f"{alert_level} Face Detected - {camera_name}"
        
        body = f"""
        Face detection alert on camera: {camera_name}
        
        Details:
        - Camera: {camera_name}
        - IP Address: {camera_ip}
        - Face Count: {face_count}
        - Confidence: {confidence:.1%}
        - Status: {face_info}
        - Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        - Location: Home
        
        {'This appears to be a recognized person.' if recognized_faces else 'Unknown person detected - please verify.'}
        """
        
        images = [image_data] if image_data else None
        return self.send_email(subject, body, images)
    
    def send_intrusion_alert(self,
                           camera_name: str,
                           camera_ip: str,
                           zone: str,
                           image_data: BinaryIO = None) -> bool:
        """Send intrusion detection alert"""
        alert_type = f"intrusion_{camera_ip}_{zone}"
        
        if not self._can_send_alert(alert_type):
            self.logger.debug(f"Alert cooldown active for {alert_type}")
            return False
        
        subject = f"🚨 Intrusion Alert - {camera_name} ({zone})"
        
        body = f"""
        INTRUSION DETECTED in restricted zone!
        
        Details:
        - Camera: {camera_name}
        - IP Address: {camera_ip}
        - Zone: {zone}
        - Severity: HIGH
        - Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        - Location: Home
        
        Immediate action recommended. Check camera feed and contact authorities if necessary.
        """
        
        images = [image_data] if image_data else None
        return self.send_email(subject, body, images)
    
    def send_system_alert(self,
                         alert_type: str,
                         message: str,
                         severity: str = "INFO") -> bool:
        """Send system alert (device offline, errors, etc.)"""
        alert_key = f"system_{alert_type}"
        
        if not self._can_send_alert(alert_key):
            self.logger.debug(f"Alert cooldown active for {alert_key}")
            return False
        
        # Map severity to emoji
        severity_emoji = {
            "INFO": "ℹ️",
            "WARNING": "⚠️",
            "ERROR": "❌",
            "CRITICAL": "🚨"
        }.get(severity, "ℹ️")
        
        subject = f"{severity_emoji} System Alert - {alert_type}"
        
        body = f"""
        Home Automation System Alert
        
        Type: {alert_type}
        Severity: {severity}
        Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        
        Message:
        {message}
        
        Please check the system status.
        """
        
        return self.send_email(subject, body)
    
    def send_daily_report(self,
                         summary: Dict[str, Any]) -> bool:
        """Send daily activity report"""
        subject = "📊 Daily Activity Report - Home Automation"
        
        # Format summary
        total_events = summary.get("total_events", 0)
        motion_events = summary.get("motion_events", 0)
        face_events = summary.get("face_events", 0)
        intrusion_events = summary.get("intrusion_events", 0)
        
        body = f"""
        Daily Activity Report
        
        Date: {datetime.now().strftime('%Y-%m-%d')}
        Period: Last 24 hours
        
        Event Summary:
        - Total Events: {total_events}
        - Motion Detections: {motion_events}
        - Face Detections: {face_events}
        - Intrusion Alerts: {intrusion_events}
        
        Camera Status:
        """
        
        # Add camera status
        cameras = summary.get("cameras", [])
        for camera in cameras:
            status = "✅ Online" if camera.get("online", False) else "❌ Offline"
            body += f"- {camera.get('name', 'Unknown')}: {status}\n"
        
        body += f"""
        
        System Status:
        - Email Alerts: {'✅ Enabled' if self.recipient_emails else '❌ Disabled'}
        - Alert Cooldown: {self.alert_cooldown // 60} minutes
        
        Report generated automatically by Home Automation System.
        """
        
        return self.send_email(subject, body)


# Configuration helper
def load_email_config(config_path: str = None) -> Dict[str, Any]:
    """Load email configuration from file or environment"""
    import yaml
    import os
    
    default_config = {
        "smtp_server": os.getenv("SMTP_SERVER", "smtp.gmail.com"),
        "smtp_port": int(os.getenv("SMTP_PORT", "587")),
        "username": os.getenv("SMTP_USERNAME", ""),
        "password": os.getenv("SMTP_PASSWORD", ""),
        "sender_email": os.getenv("SENDER_EMAIL", ""),
        "recipient_emails": os.getenv("RECIPIENT_EMAILS", "").split(",") if os.getenv("RECIPIENT_EMAILS") else [],
        "use_tls": os.getenv("USE_TLS", "true").lower() == "true",
        "use_ssl": os.getenv("USE_SSL", "false").lower() == "false",
        "alert_cooldown": int(os.getenv("ALERT_COOLDOWN", "300"))
    }
    
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                file_config = yaml.safe_load(f) or {}
                # Merge with defaults
                for key, value in file_config.items():
                    default_config[key] = value
        except Exception as e:
            get_logger(__name__).error(f"Failed to load email config from {config_path}: {e}")
    
    return default_config


# Test function
def test_email_notification():
    """Test email notification system"""
    import io
    
    # Test configuration
    config = {
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "username": "test@example.com",
        "password": "password",
        "sender_email": "test@example.com",
        "recipient_emails": ["recipient@example.com"],
        "use_tls": True,
        "alert_cooldown": 60
    }
    
    notifier = EmailNotifier(config)
    
    # Test motion alert
    print("Testing motion alert...")
    success = notifier.send_motion_alert(
        camera_name="Front Door Camera",
        camera_ip="192.168.1.100",
        confidence=0.85
    )
    print(f"Motion alert sent: {success}")
    
    # Test face alert
    print("\nTesting face alert...")
    success = notifier.send_face_alert(
        camera_name="Living Room Camera",
        camera_ip="192.168.1.101",
        confidence=0.92,
        face_count=1,
        recognized_faces=["John Doe"]
    )
    print(f"Face alert sent: {success}")
    
    # Test system alert
    print("\nTesting system alert...")
    success = notifier.send_system_alert(
        alert_type="Camera Offline",
        message="Front Door Camera has been offline for 10 minutes",
        severity="WARNING"
    )
    print(f"System alert sent: {success}")


if __name__ == "__main__":
    test_email_notification()
