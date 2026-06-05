import asyncio
from app.core.computrabajo_scraper import ComputrabajoScraper
from app.core.database import connect_to_mongo, close_mongo_connection

async def main():
    # Setup
    await connect_to_mongo()
    
    scraper = ComputrabajoScraper()
    print(f"Scraping {scraper.source_name} for 'Python'...")
    
    offers = await scraper.scrape("Python")
    print(f"Found {len(offers)} offers. Saving to MongoDB...")
    
    await scraper.save_offers(offers)
    print("Done!")
    
    # Cleanup
    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(main())
