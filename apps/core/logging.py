import logging
import re


class RedactAccountLinks(logging.Filter):
    sensitive_path = re.compile(r"(/(?:invite|recovery)/)[A-Za-z0-9_-]+")

    def filter(self, record):
        message = record.getMessage()
        redacted = self.sensitive_path.sub(r"\1[redacted]", message)
        if redacted != message:
            record.msg = redacted
            record.args = ()
        return True
