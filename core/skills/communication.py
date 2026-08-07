"""
Communication Skills - WhatsApp, calls, messages (stubs for Phase 2)
"""

import time
from typing import List
from core.skills.base import BaseSkill, SkillParameter


class WhatsAppMessageSkill(BaseSkill):
    """Send WhatsApp message (stub - requires Phase 4 Android bridge)."""
    
    @property
    def name(self) -> str:
        return "communication.whatsapp_message"
    
    @property
    def description(self) -> str:
        return "Send a WhatsApp message (requires Android bridge - Phase 4)"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="contact",
                type="string",
                description="Contact name or phone number",
                required=True,
            ),
            SkillParameter(
                name="message",
                type="string",
                description="Message to send",
                required=True,
            ),
        ]
    
    @property
    def category(self) -> str:
        return "communication"
    
    @property
    def requires_confirmation(self) -> bool:
        return True
    
    @property
    def confirmation_message(self) -> str:
        return "This will send a WhatsApp message. Confirm?"
    
    @property
    def examples(self) -> List[str]:
        return [
            "WhatsApp Ansh hello",
            "Message mom on WhatsApp I'm home",
        ]
    
    def execute(self, contact: str, message: str) -> str:
        """Send WhatsApp message (stub)."""
        return f"[Phase 4 feature] Would send WhatsApp to {contact}: {message}"


class WhatsAppDesktopSkill(BaseSkill):
    """Send WhatsApp message using the installed WhatsApp Desktop app (Windows)."""
    
    @property
    def name(self) -> str:
        return "communication.whatsapp_desktop"
    
    @property
    def description(self) -> str:
        return "Send a WhatsApp message using the installed WhatsApp Desktop app on Windows"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="contact",
                type="string",
                description="Contact name (exact or partial)",
                required=True,
            ),
            SkillParameter(
                name="message",
                type="string",
                description="Message to send",
                required=True,
            ),
        ]
    
    @property
    def category(self) -> str:
        return "communication"
    
    @property
    def requires_confirmation(self) -> bool:
        return False
    
    @property
    def confirmation_message(self) -> str:
        return "This will send a WhatsApp message via the Desktop app. Confirm?"
    
    @property
    def examples(self) -> List[str]:
        return [
            "WhatsApp desktop Ansh hello",
            "Send WhatsApp via app to mom I'm home",
        ]
    
    def execute(self, contact: str, message: str) -> str:
        """Send WhatsApp message via Desktop app using pywinauto."""
        try:
            from pywinauto import Application
        except ImportError:
            return "pywinauto not installed. Run: pip install pywinauto"
        
        try:
            # Connect to WhatsApp Desktop by class name
            app = Application(backend='uia').connect(class_name='WinUIDesktopWin32WindowClass')
            windows = app.windows()
            if not windows:
                return "WhatsApp window not found"
            window = windows[0]
            window.set_focus()
            time.sleep(0.5)
            
            # Find search box (auto_id='_r_a_', text contains 'Search')
            search_box = None
            for ctrl in window.descendants(control_type='Edit'):
                try:
                    if ctrl.automation_id() == '_r_a_':
                        search_box = ctrl
                        break
                except:
                    pass
            
            if not search_box:
                return "Could not find WhatsApp search box"
            
            # Search for contact
            search_box.click_input()
            time.sleep(0.3)
            search_box.type_keys('^a')  # Select all
            time.sleep(0.2)
            search_box.type_keys(contact)
            time.sleep(2)  # Wait for search results
            
            # Find and click contact - contacts are Buttons with "last seen" in text
            contact_found = False
            # Get the search box parent GroupBox and search for contact buttons
            try:
                parent = search_box.parent()
                for ctrl in parent.children():
                    if ctrl.friendly_class_name() == 'GroupBox':
                        # Search for buttons in this GroupBox
                        for btn in ctrl.descendants(control_type='Button'):
                            try:
                                text = btn.window_text()
                                # Contact buttons have format "Name ... last seen ..."
                                if contact.lower() in text.lower() and 'last seen' in text.lower():
                                    btn.click_input()
                                    contact_found = True
                                    time.sleep(1)
                                    break
                            except:
                                pass
                        if contact_found:
                            break
            except:
                pass
            
            # Fallback: search all buttons in window
            if not contact_found:
                for btn in window.descendants(control_type='Button'):
                    try:
                        text = btn.window_text()
                        if contact.lower() in text.lower() and 'last seen' in text.lower():
                            btn.click_input()
                            contact_found = True
                            time.sleep(1)
                            break
                    except:
                        pass
            
            if not contact_found:
                return f"Contact '{contact}' not found in WhatsApp"
            
            # Find message input box (second edit control with empty auto_id and text)
            edits = list(window.descendants(control_type='Edit'))
            msg_box = None
            for ctrl in edits:
                try:
                    if ctrl.automation_id() == '' and ctrl.window_text() == '':
                        msg_box = ctrl
                        break
                except:
                    pass
            
            if not msg_box and len(edits) > 1:
                msg_box = edits[1]  # Fallback to second edit
            
            if not msg_box:
                return "Could not find message input box"
            
            # Type and send message
            msg_box.click_input()
            time.sleep(0.3)
            msg_box.type_keys(message)
            time.sleep(0.5)
            msg_box.type_keys('{ENTER}')
            
            return f"Message sent to {contact} via WhatsApp Desktop"
            
        except Exception as e:
            return f"Failed to send WhatsApp message: {e}"


class WhatsAppCallSkill(BaseSkill):
    """Make WhatsApp call (stub)."""
    
    @property
    def name(self) -> str:
        return "communication.whatsapp_call"
    
    @property
    def description(self) -> str:
        return "Make a WhatsApp voice/video call (requires Android bridge - Phase 4)"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="contact",
                type="string",
                description="Contact name or phone number",
                required=True,
            ),
            SkillParameter(
                name="video",
                type="boolean",
                description="Video call (true) or voice call (false)",
                required=False,
                default=False,
            ),
        ]
    
    @property
    def category(self) -> str:
        return "communication"
    
    @property
    def requires_confirmation(self) -> bool:
        return True
    
    @property
    def examples(self) -> List[str]:
        return [
            "Call Ansh on WhatsApp",
            "Video call mom on WhatsApp",
        ]
    
    def execute(self, contact: str, video: bool = False) -> str:
        """Make WhatsApp call (stub)."""
        call_type = "video" if video else "voice"
        return f"[Phase 4 feature] Would make {call_type} WhatsApp call to {contact}"


class AnswerCallSkill(BaseSkill):
    """Answer incoming call (stub - requires Android bridge)."""
    
    @property
    def name(self) -> str:
        return "communication.answer_call"
    
    @property
    def description(self) -> str:
        return "Answer an incoming call (requires Android bridge - Phase 4)"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="call_type",
                type="string",
                description="Type of call: 'phone', 'whatsapp', 'teams', etc.",
                required=False,
                default="phone",
            ),
        ]
    
    @property
    def category(self) -> str:
        return "communication"
    
    @property
    def examples(self) -> List[str]:
        return [
            "Answer the call",
            "Pick up the phone",
        ]
    
    def execute(self, call_type: str = "phone") -> str:
        """Answer call (stub)."""
        return f"[Phase 4 feature] Would answer incoming {call_type} call"


class DeclineCallSkill(BaseSkill):
    """Decline incoming call (stub)."""
    
    @property
    def name(self) -> str:
        return "communication.decline_call"
    
    @property
    def description(self) -> str:
        return "Decline an incoming call (requires Android bridge - Phase 4)"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="call_type",
                type="string",
                description="Type of call: 'phone', 'whatsapp', 'teams', etc.",
                required=False,
                default="phone",
            ),
        ]
    
    @property
    def category(self) -> str:
        return "communication"
    
    @property
    def examples(self) -> List[str]:
        return [
            "Decline the call",
            "Reject the call",
        ]
    
    def execute(self, call_type: str = "phone") -> str:
        """Decline call (stub)."""
        return f"[Phase 4 feature] Would decline incoming {call_type} call"


class SendSMSSkill(BaseSkill):
    """Send SMS (stub - requires Android bridge)."""
    
    @property
    def name(self) -> str:
        return "communication.send_sms"
    
    @property
    def description(self) -> str:
        return "Send an SMS message (requires Android bridge - Phase 4)"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="phone_number",
                type="string",
                description="Recipient phone number",
                required=True,
            ),
            SkillParameter(
                name="message",
                type="string",
                description="Message to send",
                required=True,
            ),
        ]
    
    @property
    def category(self) -> str:
        return "communication"
    
    @property
    def requires_confirmation(self) -> bool:
        return True
    
    @property
    def examples(self) -> List[str]:
        return [
            "SMS 9876543210 hello",
            "Send message to dad on phone",
        ]
    
    def execute(self, phone_number: str, message: str) -> str:
        """Send SMS (stub)."""
        return f"[Phase 4 feature] Would send SMS to {phone_number}: {message}"


def register_communication_skills(registry) -> None:
    """Register all communication skills."""
    skills = [
        WhatsAppMessageSkill(),
        WhatsAppDesktopSkill(),
        WhatsAppCallSkill(),
        AnswerCallSkill(),
        DeclineCallSkill(),
        SendSMSSkill(),
    ]
    
    for skill in skills:
        registry.register(skill.to_definition())