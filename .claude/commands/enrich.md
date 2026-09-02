Launch the AflaThrive contact enrichment wizard to find new contacts and add them to contacts.csv.

Run this command:
```bash
cd ~/outreach && python enrich.py
```

The wizard will walk through:
1. Target type (Banks / Corporates / Schools)
2. Country
3. Roles to target (pre-ticked defaults, toggle to change)
4. Contacts per organisation
5. Organisation source (type names or auto-discover)
6. Review found contacts
7. Next action (dry run / test send / live send / save only)

Do not ask any questions before running. Launch the wizard directly and show all output.
If $ARGUMENTS contains org names, run non-interactively:
```bash
cd ~/outreach && python enrich.py --orgs "$ARGUMENTS"
```
