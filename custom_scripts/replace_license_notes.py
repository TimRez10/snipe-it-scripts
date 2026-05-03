from modules.config import setup_global_vars
from modules.licenses import update_license_notes, get_licenses

global_config = setup_global_vars()
logger = global_config["logger"]
HEADERS = global_config["headers"]
API_URL = global_config["api_url"]


def main():
    print("Input the phrase you want to replace:")
    old_phrase = input("> ")
    print(f"Input the phrase you want to replace \"{old_phrase}\" to:")
    new_phrase = input("> ")

    query_params = {
        "limit": 1500,
        "search": old_phrase,
    }
    license_data = get_licenses(query_params)
    
    if license_data and 'rows' in license_data:
        licenses_to_update = license_data['rows']
        
        if not licenses_to_update:
            logger.info("No licenses found with 'Sold to:' in the notes.")
            return
        
        print(f"CAUTION: change all instances of \"{old_phrase}\" to ",
              f"\"{new_phrase}\" for {len(licenses_to_update)} licenses?? (Y/n)")
        confirm = input("> ")
        if confirm != "Y":
            return
                
        for license in licenses_to_update:
            license_id = license.get('id')
            current_notes = license.get('notes')
            
            if license_id is None or current_notes is None:
                logger.warning(f"Skipping license due to missing ID or notes: {license}")
                continue

            # Check if the exact phrase exists before replacement
            if old_phrase in current_notes:
                updated_notes = current_notes.replace(old_phrase, new_phrase)
                update_license_notes(license_id, updated_notes)
            else:
                logger.debug(f"Asset ID {license_id} does not contain '{old_phrase}'. Skipping update.")

if __name__ == "__main__":
    main()