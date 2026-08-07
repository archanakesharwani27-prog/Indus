"""
Multi-Agent Base Classes - Core types for multi-agent collaboration.
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import uuid
import time
from core.llm_provider import LLMProvider
from core.agents.base import AgentStatus, AgentPlan, AgentStep, AgentResult


class AgentRole(Enum):
    """Predefined agent roles for specialization."""
    COORDINATOR = "coordinator"      # Orchestrates other agents
    PLANNER = "planner"              # Creates plans
    RESEARCHER = "researcher"        # Gathers information
    EXECUTOR = "executor"            # Executes actions
    VERIFIER = "verifier"            # Verifies results
    CRITIC = "critic"                # Reviews and critiques
    SUMMARIZER = "summarizer"        # Summarizes outputs
    SPECIALIST = "specialist"        # Domain specialist


class MessageType(Enum):
    """Types of inter-agent messages."""
    TASK_REQUEST = "task_request"       # Request another agent to do something
    TASK_RESPONSE = "task_response"     # Response to task request
    INFO_SHARE = "info_share"           # Share information
    QUERY = "query"                     # Ask a question
    QUERY_RESPONSE = "query_response"   # Answer a question
    STATUS_UPDATE = "status_update"     # Report progress
    PLAN_PROPOSAL = "plan_proposal"     # Propose a plan
    PLAN_FEEDBACK = "plan_feedback"     # Feedback on a plan
    RESULT = "result"                   # Final result
    ERROR = "error"                     # Error occurred


@dataclass
class AgentMessage:
    """Message between agents."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender_id: str = ""
    sender_role: AgentRole = AgentRole.COORDINATOR
    recipient_id: str = ""  # Empty = broadcast
    recipient_role: Optional[AgentRole] = None
    message_type: MessageType = MessageType.INFO_SHARE
    content: Dict[str, Any] = field(default_factory=dict)
    payload: Any = None
    timestamp: float = field(default_factory=time.time)
    correlation_id: str = ""  # For request-response pairing
    requires_response: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "sender_id": self.sender_id,
            "sender_role": self.sender_role.value,
            "recipient_id": self.recipient_id,
            "recipient_role": self.recipient_role.value if self.recipient_role else None,
            "message_type": self.message_type.value,
            "content": self.content,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
            "requires_response": self.requires_response,
        }


@dataclass
class AgentCapability:
    """Describes what an agent can do."""
    name: str
    description: str
    skills: List[str] = field(default_factory=list)  # Skill names
    input_types: List[str] = field(default_factory=list)
    output_types: List[str] = field(default_factory=list)


@dataclass
class AgentConfig:
    """Configuration for an agent."""
    agent_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Agent"
    role: AgentRole = AgentRole.SPECIALIST
    description: str = ""
    capabilities: List[AgentCapability] = field(default_factory=list)
    system_prompt: str = ""
    llm_provider: Optional[LLMProvider] = None
    max_retries: int = 3
    timeout_seconds: float = 60.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseAgent:
    """Base class for all agents in the multi-agent system."""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.agent_id = config.agent_id
        self.name = config.name
        self.role = config.role
        self.description = config.description
        self.capabilities = config.capabilities
        self.system_prompt = config.system_prompt
        self.llm = config.llm_provider
        self.max_retries = config.max_retries
        self.timeout_seconds = config.timeout_seconds
        self.metadata = config.metadata
        
        # State
        self.status = AgentStatus.IDLE
        self.current_task: Optional[str] = None
        self.message_handlers: Dict[MessageType, Callable] = {}
        self.shared_state: Dict[str, Any] = {}
        
        # Message queue
        self._inbox: List[AgentMessage] = []
        self._outbox: List[AgentMessage] = []
        
        # Callbacks
        self.on_message_sent: Optional[Callable[[AgentMessage], None]] = None
        self.on_message_received: Optional[Callable[[AgentMessage], None]] = None
        self.on_task_start: Optional[Callable[[str], None]] = None
        self.on_task_complete: Optional[Callable[[str, Any], None]] = None
        self.on_task_failed: Optional[Callable[[str, str], None]] = None
        
        self._register_default_handlers()
    
    def _register_default_handlers(self) -> None:
        """Register default message handlers."""
        self.message_handlers[MessageType.TASK_REQUEST] = self._handle_task_request
        self.message_handlers[MessageType.QUERY] = self._handle_query
        self.message_handlers[MessageType.INFO_SHARE] = self._handle_info_share
        self.message_handlers[MessageType.PLAN_FEEDBACK] = self._handle_plan_feedback
    
    def _handle_task_request(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Handle a task request from another agent."""
        task = message.content.get("task", "")
        context = message.content.get("context", {})
        
        if self.on_task_start:
            self.on_task_start(task)
        
        try:
            result = self.execute_task(task, context)
            
            if self.on_task_complete:
                self.on_task_complete(task, result)
            
            if message.requires_response:
                return AgentMessage(
                    sender_id=self.agent_id,
                    sender_role=self.role,
                    recipient_id=message.sender_id,
                    message_type=MessageType.TASK_RESPONSE,
                    content={"task": task, "result": result, "success": True},
                    correlation_id=message.correlation_id or message.id,
                )
        except Exception as e:
            if self.on_task_failed:
                self.on_task_failed(task, str(e))
            
            if message.requires_response:
                return AgentMessage(
                    sender_id=self.agent_id,
                    sender_role=self.role,
                    recipient_id=message.sender_id,
                    message_type=MessageType.ERROR,
                    content={"task": task, "error": str(e)},
                    correlation_id=message.correlation_id or message.id,
                )
        
        return None
    
    def _handle_query(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Handle a query from another agent."""
        question = message.content.get("question", "")
        context = message.content.get("context", {})
        
        try:
            answer = self.answer_query(question, context)
            
            if message.requires_response:
                return AgentMessage(
                    sender_id=self.agent_id,
                    sender_role=self.role,
                    recipient_id=message.sender_id,
                    message_type=MessageType.QUERY_RESPONSE,
                    content={"question": question, "answer": answer},
                    correlation_id=message.correlation_id or message.id,
                )
        except Exception as e:
            if message.requires_response:
                return AgentMessage(
                    sender_id=self.agent_id,
                    sender_role=self.role,
                    recipient_id=message.sender_id,
                    message_type=MessageType.ERROR,
                    content={"question": question, "error": str(e)},
                    correlation_id=message.correlation_id or message.id,
                )
        
        return None
    
    def _handle_info_share(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Handle shared information from another agent."""
        self.receive_info(message.content, message.sender_id)
        return None
    
    def _handle_plan_feedback(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Handle feedback on a proposed plan."""
        plan_id = message.content.get("plan_id", "")
        feedback = message.content.get("feedback", "")
        self.receive_plan_feedback(plan_id, feedback, message.sender_id)
        return None
    
    def receive_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Process an incoming message."""
        self._inbox.append(message)
        
        if self.on_message_received:
            self.on_message_received(message)
        
        handler = self.message_handlers.get(message.message_type)
        if handler:
            return handler(message)
        return None
    
    def send_message(self, message: AgentMessage) -> None:
        """Send a message (added to outbox for delivery)."""
        message.sender_id = self.agent_id
        message.sender_role = self.role
        self._outbox.append(message)
        
        if self.on_message_sent:
            self.on_message_sent(message)
    
    def get_outbox(self) -> List[AgentMessage]:
        """Get and clear the outbox."""
        messages = self._outbox.copy()
        self._outbox.clear()
        return messages
    
    def execute_task(self, task: str, context: Dict[str, Any]) -> Any:
        """Execute a task. Override in subclasses."""
        raise NotImplementedError
    
    def answer_query(self, question: str, context: Dict[str, Any]) -> Any:
        """Answer a query. Override in subclasses."""
        if self.llm:
            prompt = f"{self.system_prompt}\n\nQuestion: {question}\nContext: {context}\nAnswer:"
            return self.llm.chat([{"role": "user", "content": prompt}])
        return "No LLM available for query answering."
    
    def receive_info(self, info: Dict[str, Any], from_agent: str) -> None:
        """Receive shared information. Override to store relevant info."""
        self.shared_state[f"from_{from_agent}"] = info
    
    def receive_plan_feedback(self, plan_id: str, feedback: str, from_agent: str) -> None:
        """Receive feedback on a plan. Override to incorporate feedback."""
        pass
    
    def propose_plan(self, goal: str, context: Dict[str, Any]) -> AgentPlan:
        """Propose a plan for a goal. Override in planner agents."""
        raise NotImplementedError
    
    def get_capabilities_summary(self) -> str:
        """Get a summary of agent capabilities for other agents."""
        caps = []
        for cap in self.capabilities:
            caps.append(f"- {cap.name}: {cap.description}")
        return f"{self.name} ({self.role.value}):\n" + "\n".join(caps)


class AgentMessageBus:
    """Central message bus for inter-agent communication."""
    
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self.message_log: List[AgentMessage] = []
        self.subscriptions: Dict[str, List[str]] = {}  # topic -> agent_ids
    
    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent with the bus."""
        self.agents[agent.agent_id] = agent
        agent.on_message_sent = self._on_message_sent
    
    def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent."""
        if agent_id in self.agents:
            del self.agents[agent_id]
    
    def _on_message_sent(self, message: AgentMessage) -> None:
        """Handle message sent by an agent."""
        self.message_log.append(message)
        self._deliver_message(message)
    
    def _deliver_message(self, message: AgentMessage) -> None:
        """Deliver message to recipient(s)."""
        if message.recipient_id:
            # Direct message
            if message.recipient_id in self.agents:
                response = self.agents[message.recipient_id].receive_message(message)
                if response:
                    self._deliver_message(response)
        elif message.recipient_role:
            # Role-based broadcast
            for agent in self.agents.values():
                if agent.role == message.recipient_role:
                    response = agent.receive_message(message)
                    if response:
                        self._deliver_message(response)
        else:
            # Broadcast to all
            for agent in self.agents.values():
                if agent.agent_id != message.sender_id:
                    response = agent.receive_message(message)
                    if response:
                        self._deliver_message(response)
    
    def send_message(self, message: AgentMessage) -> None:
        """Send a message through the bus."""
        self._deliver_message(message)
    
    def broadcast(self, sender_id: str, sender_role: AgentRole, 
                  message_type: MessageType, content: Dict[str, Any]) -> None:
        """Broadcast a message to all agents."""
        message = AgentMessage(
            sender_id=sender_id,
            sender_role=sender_role,
            message_type=message_type,
            content=content,
        )
        self.send_message(message)
    
    def request_response(
        self,
        sender_id: str,
        sender_role: AgentRole,
        recipient_id: str,
        message_type: MessageType,
        content: Dict[str, Any],
        timeout: float = 30.0,
    ) -> Optional[AgentMessage]:
        """Send a request and wait for response."""
        correlation_id = str(uuid.uuid4())
        message = AgentMessage(
            sender_id=sender_id,
            sender_role=sender_role,
            recipient_id=recipient_id,
            message_type=message_type,
            content=content,
            correlation_id=correlation_id,
            requires_response=True,
        )
        
        # Register a temporary handler on the SENDER for the response
        response_holder = {"response": None, "received": False}
        
        def response_handler(msg: AgentMessage):
            if msg.correlation_id == correlation_id:
                response_holder["response"] = msg
                response_holder["received"] = True
        
        # Determine expected response message type
        response_type_map = {
            MessageType.TASK_REQUEST: MessageType.TASK_RESPONSE,
            MessageType.QUERY: MessageType.QUERY_RESPONSE,
            MessageType.PLAN_PROPOSAL: MessageType.PLAN_FEEDBACK,
        }
        expected_response_type = response_type_map.get(message_type, MessageType.TASK_RESPONSE)
        
        # Temporarily add handler on sender for response
        if sender_id in self.agents:
            original_handler = self.agents[sender_id].message_handlers.get(expected_response_type)
            self.agents[sender_id].message_handlers[expected_response_type] = lambda m: response_handler(m) or (original_handler(m) if original_handler else None)
        
        self.send_message(message)
        
        # Wait for response
        start = time.time()
        while not response_holder["received"] and (time.time() - start) < timeout:
            time.sleep(0.01)
        
        # Restore original handler
        if sender_id in self.agents:
            if original_handler:
                self.agents[sender_id].message_handlers[expected_response_type] = original_handler
            else:
                self.agents[sender_id].message_handlers.pop(expected_response_type, None)
        
        return response_holder["response"]


class SharedState:
    """Shared state store for multi-agent collaboration."""
    
    def __init__(self):
        self._state: Dict[str, Any] = {}
        self._locks: Dict[str, bool] = {}
        self._subscribers: Dict[str, List[Callable]] = {}
    
    def set(self, key: str, value: Any, agent_id: str = "") -> None:
        """Set a value in shared state."""
        self._state[key] = {"value": value, "updated_by": agent_id, "timestamp": time.time()}
        if key in self._subscribers:
            for callback in self._subscribers[key]:
                try:
                    callback(key, value)
                except Exception:
                    pass
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from shared state."""
        entry = self._state.get(key)
        if entry:
            return entry["value"]
        return default
    
    def delete(self, key: str) -> bool:
        """Delete a key from shared state."""
        if key in self._state:
            del self._state[key]
            return True
        return False
    
    def subscribe(self, key: str, callback: Callable[[str, Any], None]) -> None:
        """Subscribe to changes on a key."""
        if key not in self._subscribers:
            self._subscribers[key] = []
        self._subscribers[key].append(callback)
    
    def unsubscribe(self, key: str, callback: Callable) -> None:
        """Unsubscribe from changes on a key."""
        if key in self._subscribers:
            self._subscribers[key].remove(callback)
    
    def get_all(self) -> Dict[str, Any]:
        """Get all shared state."""
        return {k: v["value"] for k, v in self._state.items()}
    
    def acquire_lock(self, key: str, agent_id: str, timeout: float = 5.0) -> bool:
        """Acquire a lock on a key."""
        start = time.time()
        while time.time() - start < timeout:
            if key not in self._locks:
                self._locks[key] = agent_id
                return True
            time.sleep(0.01)
        return False
    
    def release_lock(self, key: str, agent_id: str) -> bool:
        """Release a lock on a key."""
        if self._locks.get(key) == agent_id:
            del self._locks[key]
            return True
        return False