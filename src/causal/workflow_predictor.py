from typing import List, Dict, Tuple
from .event_store import EventStore

class WorkflowPredictor:
    """
    Predicts the next files a user is likely to edit based on historical editing sequences
    using a simple Markov Chain model.
    """
    def __init__(self, event_store: EventStore):
        self.event_store = event_store
        self.transition_counts: Dict[str, Dict[str, int]] = {}
        self._build_model()

    def _build_model(self):
        """Rebuild the Markov transition matrix from the event store"""
        self.transition_counts.clear()
        
        # Extract only file_edit events in chronological order
        edit_events = [e for e in self.event_store.events if e.event_type == "file_edit"]
        
        for i in range(len(edit_events) - 1):
            current_file = edit_events[i].source
            next_file = edit_events[i+1].source
            
            # Skip self-transitions (e.g. saving the same file twice)
            if current_file == next_file:
                continue
                
            if current_file not in self.transition_counts:
                self.transition_counts[current_file] = {}
                
            if next_file not in self.transition_counts[current_file]:
                self.transition_counts[current_file][next_file] = 0
                
            self.transition_counts[current_file][next_file] += 1

    def predict_next_files(self, current_file: str, top_k: int = 3) -> List[Tuple[str, float]]:
        """
        Predict the most likely next files to be edited.
        Returns a list of (file_path, probability) tuples.
        """
        self._build_model() # Ensure model is up to date
        
        if current_file not in self.transition_counts:
            return []
            
        transitions = self.transition_counts[current_file]
        total_transitions = sum(transitions.values())
        
        if total_transitions == 0:
            return []
            
        # Calculate probabilities
        probabilities = [
            (target_file, count / total_transitions)
            for target_file, count in transitions.items()
        ]
        
        # Sort by highest probability
        probabilities.sort(key=lambda x: x[1], reverse=True)
        
        return probabilities[:top_k]
