from modules.config import setup_global_vars
from modules.assets import update_asset_notes, get_assets

global_config = setup_global_vars()
logger = global_config["logger"]
HEADERS = global_config["headers"]
API_URL = global_config["api_url"]

def main():
    """Fetches assets and updates their notes from a specified old phrase to a new phrase."""
    print("Input the phrase you want to replace:")
    old_phrase = input("> ")
    print(f"Input the phrase you want to replace \"{old_phrase}\" to:")
    new_phrase = input("> ")
  
    query_params = {
        "limit": 1500,
        "search": old_phrase,
    }
    asset_data = get_assets(query_params)
    
    if asset_data and 'rows' in asset_data:
        assets_to_update = asset_data['rows']
        
        if not assets_to_update:
            logger.info(f"No assets found with '{old_phrase}' in the notes.")
            return
        
        print(f"CAUTION: change all instances of \"{old_phrase}\" to ",
              f"\"{new_phrase}\" for {len(assets_to_update)} assets? (Y/n)")
        confirm = input("> ")
        if confirm != "Y":
            return
        
        for asset in assets_to_update:
            asset_id = asset.get('id')
            current_notes = asset.get('notes')
            
            if asset_id is None or current_notes is None:
                logger.warning(f"Skipping asset due to missing ID or notes: {asset}")
                continue

            # Check if the exact phrase exists before replacement
            if old_phrase in current_notes:
                updated_notes = current_notes.replace(old_phrase, new_phrase)
                update_asset_notes(asset_id, updated_notes)
            else:
                logger.debug(f"Asset ID {asset_id} does not contain '{old_phrase}'. Skipping update.")

if __name__ == "__main__":
    main()