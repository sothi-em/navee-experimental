# Agent Guidelines

## Python server testing

When testing the Python server (`backend/server.py`):

- NEVER bind to the server's normal development port. Always use a different, free port for the test instance.
- Spawn the test server in your own thread (or subprocess) and tear it down when the test is done — do not leave a server process running after the test, and do not rely on a pre-existing server instance.
