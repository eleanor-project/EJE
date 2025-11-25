import yaml, time, os

class Retrainer:
    def __init__(self, config, audit_logger):
        self.batch_size = config.get('retrain_batch_size', 25)
        self.event_buffer = []
        self.data_path = config.get('data_path', './eleanor_data')
        self.audit = audit_logger

    def maybe_retrain(self, agg, details):
        if agg['overall_verdict'] != 'REVIEW' and agg['avg_confidence'] > 0.8:
            self.event_buffer.append((agg, details))
        if len(self.event_buffer) >= self.batch_size:
            self.snap_and_retrain()

    def snap_and_retrain(self):
        print("Retraining triggered: snapshot and adaptive logic.")
        fname = os.path.join(self.data_path, f"retrain_snapshot_{int(time.time())}.yml")
        with open(fname, "w") as f:
            yaml.safe_dump(self.event_buffer, f)
        # Simulate critic weights adaptation
        for agg, details in self.event_buffer:
            for d in details:
                if d['verdict'] == agg['overall_verdict']:
                    d['weight'] = min(d.get('weight', 1.0) + 0.05, 2.0)
                else:
                    d['weight'] = max(d.get('weight', 1.0) - 0.05, 0.5)
        self.event_buffer.clear()
