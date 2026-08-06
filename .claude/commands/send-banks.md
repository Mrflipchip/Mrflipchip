Send emails to specific banks only. $ARGUMENTS should be a comma-separated list of bank names.

Example: /send-banks BDO,RCBC,Metrobank

Run this command, substituting the bank names from $ARGUMENTS:
```bash
cd ~/outreach && python send_pipeline.py --banks "$ARGUMENTS"
```

If $ARGUMENTS is empty, ask me which banks to target before running.
Show the full output as it runs.
