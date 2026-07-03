# Configuration Files

Configuration files describe how a framework pipeline is assembled.

Each section maps a core interface, such as `document_loader` or `validator`,
to the implementation/provider that should be used for that role. This keeps
provider choices outside Python code and makes workflows easier to swap or
extend.

Provider factories and pipeline execution are intentionally handled elsewhere.
