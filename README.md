# Snipe-IT Automations (ITAMS)

## Overview
This repository contains scripts that automatically manage asset and license seat assignments in Snipe-IT based on data exports from various vendor admin consoles (via web scraping or APIs). Works on both Linux and Windows.

## Usage

0. Clone this repository to your local machine and navigate to its directory.
1. Create and activate a Python virtual environment, then install dependencies:
   - Linux:
     ```
     python3 -m venv venv
     source venv/bin/activate
     pip install -r requirements.txt
     ```
   - Windows:
     ```
     python -m venv venv
     venv\Scripts\activate
     pip install -r requirements.txt
     ```
2. Duplicate `secrets.json.template` and rename it to `secrets.json`. Fill in:
   - `SNIPEIT_API_URL` and `SNIPEIT_API_KEY`
   - Optionally `DATTO_API_KEY` and `DATTO_API_SECRET` if using Datto
3. Duplicate the `app_config.json.template` configuration file and rename it to `app_config.json`. Update it so it reflects your Snipe-IT and vendor portals setup ( `company_domain`, vendor URLs, `LICENSE_ID`s, and `PRODUCT_TO_LICENSE_ID` mappings).
4. For Selenium web scraping, download the appropriate WebDriver for your browser and OS, and ensure it's in your system PATH.
5. If using Linux, install the PowerShell Core package (pwsh) for your distribution to support Microsoft and Discovered Apps scripts.
6. For Microsoft and Discovered Apps scripts, install the MS Graph PowerShell module, and ensure you have the necessary permissions.

### Run the tool:

- Linux:
```bash
python3 update_itams.py
python3 update_itams.py --help
python3 update_itams.py --script license_scripts/adobe.py
```
- Windows:
```bash
python update_itams.py
python update_itams.py --help
python update_itams.py --script license_scripts/adobe.py
```

### Follow the prompts:

1. Choose whether to update **Assets** or **Licenses** by entering the number shown.
2. If you choose **Licenses**, select one or more vendors from the numbered list to run their update scripts.
3. If you choose **Custom Script**, select a script from the custom script list.
4. The script will run the selected updater automatically.

## Available Scripts

### Asset Management

These scripts update assets in Snipe-IT.

- Update Monitors

### License Management

These scripts manage paid software licenses with specific seat limits.

- Adobe (licensed)
- Autodesk
- Bluebeam
- Datto
- Microsoft
- PDF-xChange
- KnowBe4

---

### User List

These scripts manage unlimited-user applications (and for some vendors, also reconcile seats and notes as applicable).

- Adobe (unlicensed)
- Gatemanager
- Unifi
- Procore
- SolidWorks PDM
- SolidProfessor
- Wordpress (through phpMyAdmin)

---

### Custom Scripts

These scripts provide one-off maintenance helpers and bulk update utilities.

- Bulk Update Any License
- Replace Asset Notes
- Replace License Notes
- Update Asset Notes Based on Price

---

### Discovered Apps

In Microsoft Intune, **Discovered Apps** is a feature that provides a software inventory of applications installed on devices managed by Intune. It acts as a central record of applications detected on enrolled devices.
The purpose of this script is to record some of the software that wasn't covered by the other scripts to ITAMS.

- When adding software to the `app_config.json` configuration file, "product_name" matches the exact string, while "*product_name" matches the substring