# Chanmerge
![Python Version](https://img.shields.io/badge/python-3.12%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Topic](https://img.shields.io/badge/topic-astrophysics-red)

**Chanmerge** is a specialized Python library designed to automate the retrieval, reprocessing, and merging of **Chandra X-ray Observatory** data.

---

## Scientific Workflow

The library automates a rigorous X-ray analysis chain to ensure data consistency and reproducibility:

*   **Catalog Cross-Matching:** Dynamically queries the `chanmaster` archival database using `astroquery.heasarc` to ensure all relevant spatial data within the user-defined search radius is captured.
*   **Calibration Alignment:** Standardizes the reprocessing of raw event files using the `chandra_repro` algorithm, ensuring every observation is synchronized with the latest CALDB (Calibration Database) updates.
*   **Flux Synthesis:** Automates the multi-step `merge_obs` process, including exposure map generation and aspect solution handling, to produce integrated flux images across specified energy bands.
*   **Automated Workspace Management:** Sanitizes file structures and handles directory-level organization, mitigating the risk of manual processing errors during large-scale archival studies.

---

## Installation

### Prerequisites
*   **Python 3.12+**
*   **CIAO 4.16+** (Must be initialized in the environment)

### Setup
```bash
pip install chanmerge
```

---

## Quick Start
To begin your analysis, use the following Python command:

```python
from chanmerge import auto_merge_obs

auto_merge_obs(
    ra="13:25:27.6", 
    dec="-43:01:09", 
    radius_arcmin=15.0
)
```
---

## Author
**Ahmet Sercan Kıyak**  
*Boğaziçi University, Department of Physics*

---

## License
This project is licensed under the **MIT License**.
