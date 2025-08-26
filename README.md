# Replication Package for *Measuring Information Diffusion in Code Review at Spotify*

This replication package contains the data, scripts, and documentation used in the study:

> **Measuring Information Diffusion in Code Review at Spotify**, submitted to *Empirical Software Engineering (EMSE)*, [2025].

---

## 📂 Repository Structure
```
.
├── crawl.ipynb # How we crawled the raw data
├── load.ipynb # How we translated the data into the study model
├── anonymize.ipynb # How we anonymized the data
├── analyze.ipynb # How we analyzed the data
├── data/ # Anonymized dataset (must be unpacked separately)
├── raw_data/ # Raw data (not shared, due to confidentiality restrictions)
└── csv/ # Results as CSV files used in the paper
```

---

## How to Reproduce

1. Download the latest [release](https://github.com/michaeldorner/measuring-information-diffusion-in-code-review-at-spotify/releases)

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Unpack `data.zip`:

```bash
unzip data.zip -d .
```

4. Run Jupyter notebooks, for example, `analyze.ipynb`


⚠️ Note on similarity matrix computation:
Computing the similarity matrix is computationally expensive and may take several days depending on your hardware.
For convenience, the data we share via Zenodo already includes a precomputed similarity matrix.

---

## 📄 License

The code in this replication package is released under the MIT License and the data under the CC BY-SA License.

---

## 👩‍💻 Contact

For questions or issues, feel free to contact:

**Michael Dorner**  
Email: michael.dorner@th-nuernberg.de 
Affiliation: Blekinge Institute of Technology, Sweden, and Technische Hochschule Nürnberg, Germany
