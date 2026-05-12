# CPEE Compliance Transformation Service

This project provides a service for automating process model modifications to ensure compliance within the Cloud Process Execution Engine (CPEE). It employs a two-phase approach to compliance: ex-ante transformation and runtime enforcement via a voting mechanism.

## Overview

The service listens for notifications from CPEE, parses compliance requirements, and modifies the process description (XML) to either enforce these requirements or prepare for runtime enforcement.

### Key Features

- **Ex-ante Transformation**: Modifies the process XML before execution to incorporate compliance patterns.
- **Runtime Enforcement**: Uses CPEE's voting mechanism (`vote_syncing_before`, `vote_syncing_after`) to dynamically manage compliance during process execution.
- **Requirement Parsing**: Supports a custom domain-specific language for defining compliance requirements (e.g., `precedence`, `recurring`, `maxExecTime`).
- **Semantic Endpoint Resolution**: Uses sentence embeddings to match activities in requirements to actual process endpoints.

## Components

- `transformer.py`: The main FastAPI application providing the transformation and voting endpoints.
- `ComplianceAST.py` & `reqparser.py`: Responsible for parsing requirements and traversing the process tree to apply transformations.
- `transformerPatterns.py`: Implements the logic for various compliance patterns.
- `modifierpatterns.py`: Handles modifications to the process tree when patterns are already explicitly present.
- `jobs.py`: Manages the lifecycle of compliance-related subprocesses during the voting phases.
- `patterns.py`: Provides XML templates for different compliance enforcement patterns.

## API Endpoints

- **POST `/transform`**:
    - Receives a CPEE notification containing the process description and compliance requirements.
    - Parses requirements and transforms the XML.
    - Generates jobs for runtime enforcement.
    - Returns the modified XML (and sends it to a compliance log).
- **POST `/vote_syncing_before`**:
    - Triggered before an activity starts.
    - Handles jobs that need to be executed before the activity (e.g., opening a monitoring subprocess).
- **POST `/vote_syncing_after`**:
    - Triggered after an activity finishes.
    - Handles jobs that need to be executed after the activity (e.g., abandoning a monitoring subprocess).

## Setup and Running

### Prerequisites

- Python 3.x
- Dependencies listed in the project (FastAPI, uvicorn, requests, yaml, sentence-transformers, etc.)

### Running the Service

Start the service by running:

```bash
python3 transformer.py
```

Optional verbose logging:

```bash
python3 transformer.py --verbose
```

The service runs on port `9322` by default.

## Testing

You can run local tests using the provided scripts:

```bash
python3 local_test_script.py
```

This will process XML files in the `Inputs/` directory and generate modified versions in the `Outputs/` directory.
