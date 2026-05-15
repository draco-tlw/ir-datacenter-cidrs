import asyncio
import aiohttp
import ipaddress
import logging
import sys

logging.basicConfig(level=logging.INFO, format='%(message)s')

TARGET_DATACENTERS = [
    "202468", "205585", # Noyan Abr Arvan (ArvanCloud)
    "49801", "204533", "202319", # Hezardastan Cloud (CafeBazaar/Sotoon)
    "25184",            # Afranet
    "58262",            # Negah Roshan Pars (ParsPack)
    "48434",            # Tebyan-e-Noor (Tebyan IDC)
    "48147",            # Asre Pardazeshe Amin (Amin IDC)
    
    "43754", "211421", "41689", "51433", "203000", # Asiatech
    "31549", "34369",   # Aria Shatel
    "60976", "16322", "61061", # Parsan Lin (ParsOnline)
    "42337",            # Respina Networks
    "49100", "34918", "3263", "201540", "201015", "200816", # Pishgaman
    "50810", "47330",   # Mobin Net (Datacenter Division)
    "24631", "206065",  # Fanap (Pasargad Arian)
    "51074", "59442",   # Mabna
    "41881", "62442", "61036", "60637", # Fanava Group
    "25124",            # Datak
    "39074",            # Sepanta

    "61173",            # Green Web (IranServer)
    "59441", "48029",   # NOAVARAN SHABAKEH SABZ (Hostiran)
    "208555", "204544", "51026", # Dade Pardazi Mobinhost
    "44285", "60248", "48715",   # Sefroyek Pardaz (01 Pars)
    "201999",           # Fanavari Serverpars
    "57497",            # Faraso Samaneh Pasargad (Faraso)
    "204213",           # Netmihan (MihanWebHost)
    "48551",            # Sindad Network Technology
    "212216",           # Netafraz Iranian
    "48391",            # Pars Data Processing
    "39501", "59703",   # Parvaresh Dadeha Co (DPCo)
    "47376", "47308",   # Web Gostaran Bandar
    "205647",           # PARDIS FANVARI PARTAK
    "60631",            # Vandad Vira Hooman
    "213807",           # Fanavaran Mehr Vatan Tehran Server Group

    "34412",            # Saba Abr Mizban
    "214824",           # Abr Gostar Arianet
    "214171",           # Foojan Cloud
    "213969",           # Rayanesh Pardis Saman (Cloud)
    "204104",           # Giti Secure Cloud
    "198154",           # Pars Abr Toseeh
    "215350",           # Abr Ayande Iranian Co
    "213665",           # PARMIN CLOUD COMPUTING
    "212544",           # Darvag Cloud Infrastructure
    "212076",           # Dadeh Rayanesh Abri Pardis
    "210405",           # Vira Cloud DataCenter
    "215633",           # Abr Baran
    "48281",            # Abr Tose'eh Darya

    "64458", "201227",  # Mizban Dade Pasargad
    "64434",            # Mizban Amvaj Sahel
    "64428",            # Mizban Web Paytakht
    "214922",           # FanAvaran Mihan Mizban
    "213953",           # Mizban Dadeh Pardis
    "213644",           # Iranian Server Processing
    "215938",           # Mizban Pardazesh Nasle Farda
    "215767",           # Mizban Pardazesh Pouyan
    "214567",           # Mizbani Hooshmand Mehr Afarin
    "214431",           # Mizban Gostar Dade Alvand
    "214361",           # Mizban Dadeh Pardazi Pasargad
    "200324",           # Mizban Abri Iman
    "201634",           # Mizban Dade Shetaban
    "197937",           # Mizban Dadeh Roham
    "35766",            # Mizbani Dadehaye Mabna
    
    "44889", "64399",   # Farhang Azma
    "44932",            # Saba (SabaNet)
    "21341",            # Soroush Rasanheh
    "204834", "206325", "204865", # Shabakieh Isfahan
    "51235",            # ARAAX DADEH GOSTAR
    "48944",            # Khalij Fars Ettela Resan
    "48903",            # Rasaneh Mehr Vatan
    "215496",           # DyarWeb
    "216344",           # Enteghal Dade Arya Sarv
    "214151",           # Amin Asia Cloud Data
    "207680",           # Pars Databan
    "200796",           # Data Pardaz Afraz
    "49556",            # Web Dadeh Paydar
    "48431",            # Bozorg Net-e Aria
]

async def fetch_cidr(session, asn, semaphore, retries=4):
    url = f"https://stat.ripe.net/data/announced-prefixes/data.json?resource=AS{asn}"
    
    async with semaphore:
        for attempt in range(retries):
            try:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        prefixes = [item['prefix'] for item in data['data']['prefixes']]
                        return asn, prefixes
                    elif response.status == 429:
                        await asyncio.sleep((2 ** attempt) + 1)
                    else:
                        await asyncio.sleep(1)
            except (aiohttp.ClientError, asyncio.TimeoutError):
                await asyncio.sleep(1)
                
        return asn, []

async def main():
    print("=" * 65)
    print("\033[1;96m[*] Riftway - Datacenter Precision Extractor (Whitelist Mode)\033[0m")
    print("=" * 65)
    
    if not TARGET_DATACENTERS:
        logging.error("\033[91m[!] Error: TARGET_DATACENTERS list is empty! Please insert the ASNs.\033[0m")
        sys.exit(1)
        
    raw_cidrs_set = set()
    connector = aiohttp.TCPConnector(limit=20, keepalive_timeout=30)
    semaphore = asyncio.Semaphore(15)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        logging.info(f"[*] Phase 1: Locking onto {len(TARGET_DATACENTERS)} Major Iranian Datacenters...")
        
        tasks = [fetch_cidr(session, asn, semaphore) for asn in TARGET_DATACENTERS]
        total = len(TARGET_DATACENTERS)
        completed = 0
        
        for future in asyncio.as_completed(tasks):
            asn, cidrs = await future
            completed += 1
            
            valid_ipv4 = 0
            for cidr in cidrs:
                if ':' not in cidr:
                    raw_cidrs_set.add(cidr)
                    valid_ipv4 += 1
                    
            sys.stdout.write(f"\r\033[K[>] Progress: {completed}/{total} | Extracted AS{asn:<6} ({valid_ipv4} subnets)")
            sys.stdout.flush()

    print("\n")
    logging.info("-" * 65)
    logging.info("[*] Phase 2: Compiling and optimizing subnets...")
    
    raw_networks = [ipaddress.ip_network(cidr, strict=False) for cidr in raw_cidrs_set]
    optimized_networks = list(ipaddress.collapse_addresses(raw_networks))
    
    output_file = "iran_datacenter_cidrs.txt"
    with open(output_file, "w") as f:
        for net in optimized_networks:
            f.write(str(net) + "\n")
            
    logging.info("=" * 65)
    logging.info(f"\033[1;92m[+] Sniper Operation Complete!\033[0m")
    logging.info(f"[*] Target ASNs          : {len(TARGET_DATACENTERS)}")
    logging.info(f"[*] Unique IPv4 Subnets  : {len(raw_cidrs_set)}")
    logging.info(f"[*] Optimized CIDR Blocks: {len(optimized_networks)}")
    logging.info(f"[*] File Saved To        : '{output_file}'")
    logging.info("=" * 65)

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\033[91m[!] Process immediately halted by user (Ctrl+C).\033[0m")
        sys.exit(0)
