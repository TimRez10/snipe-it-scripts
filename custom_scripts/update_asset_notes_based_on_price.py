from modules.config import setup_global_vars
from modules.assets import update_asset_notes, get_assets

global_config = setup_global_vars()
logger = global_config["logger"]

def main():
    """Fetches assets and updates their notes from a specified old phrase to a new phrase."""
    print("Input the price you want to add a note for:")
    price = float(input("> "))
    print(f"Input the phrase you want to add to those devices notes:")
    phrase = input("> ")
  
    query_params = {
        "limit": 1500,
        "category_id": 3,
    }

    asset_data = get_assets(query_params)
    
    if asset_data and 'rows' in asset_data:
        assets_to_update = asset_data['rows']
        
        if not assets_to_update:
            logger.info(f"No assets found with '{price}' in the notes.")
            return
        
        print(f"CAUTION: update all instances of ${price} devices to add the note ",
              f"\"{phrase}\" for {len(assets_to_update)} assets? (Y/n)")
        confirm = input("> ")
        if confirm != "Y":
            print("Exiting")
            return
        
        for asset in assets_to_update:
            asset_id = asset.get('id')
            current_notes = asset.get('notes')
            asset_price = float(asset.get('purchase_cost').replace(",", ""))
            
            if asset_id is None: 
                logger.warning(f"Skipping asset due to missing ID or notes: {asset_id}")
                continue

            if current_notes is None:
                current_notes = ""

            # Check if the exact price exists before replacement
            if price == asset_price:
                updated_notes = current_notes + f"\n#{phrase}"
                logger.info(f"Updating asset ID: {asset_id}")
                update_asset_notes(asset_id, updated_notes)
            else:
                logger.info(f"Asset ID {asset_id} does not have price '{price}', it costs '{asset_price}'. Skipping update.")

if __name__ == "__main__":
    main()