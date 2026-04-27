import asyncio
import aiohttp
import ipaddress
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')

TARGET_ASNS = [
    "43754",  # Afranet
    "25184",  # Afranet (Secondary/Older IPs)
    "43288",  # ArvanCloud
    "43275",  # Asiatech
    "42306",  # Respina
    "31549",  # Shatel
    "16322",  # ParsOnline
    "58224",  # MihanWebHost
    
    "200406", # Javid Berbid Mamasani (JeyServer)
    "211881", # Tahlil Dadeh Novin Fadak
    "60976",  # Parsan Lin Co
    "59441",  # Hostiran Network
    
    "51493",  # Sabanet (Neda Gostar)
    "41689",  # Soroush Resaneh
    "49100",  # MobinNet (Often used for cloud/B2B)
    "39508",  # Irancell (Datacenter/Cloud divisions)
    "48359",  # Mabna Telecom
]

async def fetch_cidr(session, asn, retries=3):

    url = f"https://stat.ripe.net/data/announced-prefixes/data.json?resource=AS{asn}"
    
    for attempt in range(retries):
        try:
            async with session.get(url, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    prefixes = [item['prefix'] for item in data['data']['prefixes']]
                    return asn, prefixes
                elif response.status == 429:
                    await asyncio.sleep(2 ** attempt) 
        except Exception as e:
            logging.warning(f"[!] Network Error on AS{asn} (Attempt {attempt+1}/{retries})")
            await asyncio.sleep(1)
            
    logging.error(f"[-] Failed to fetch data for AS{asn} after {retries} attempts.")
    return asn, []

async def main():
    logging.info("[*] Phase 1: Initiating High-Speed BGP CIDR Extraction via RIPE...")
    
    raw_networks = []
    
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_cidr(session, asn) for asn in TARGET_ASNS]
        results = await asyncio.gather(*tasks)
        
        for asn, cidrs in results:
            valid_ipv4_count = 0
            for cidr in cidrs:
                try:
                    net = ipaddress.ip_network(cidr, strict=False)
                    if net.version == 4:
                        raw_networks.append(net)
                        valid_ipv4_count += 1
                except ValueError:
                    continue   
            
            logging.info(f"[+] AS{asn:<6} -> Extracted {valid_ipv4_count:<4} IPv4 blocks.")

    # ---------------------------------------------------------
    logging.info("[-] Optimizing and collapsing overlapping subnets...")
    optimized_networks = list(ipaddress.collapse_addresses(raw_networks))
    
    output_file = "target_cidrs_optimized.txt"
    with open(output_file, "w") as f:
        for net in optimized_networks:
            f.write(str(net) + "\n")
            
    logging.info("-" * 50)
    logging.info(f"[*] Operation Complete!")
    logging.info(f"[*] Raw IPv4 blocks: {len(raw_networks)}")
    logging.info(f"[*] Optimized/Unique blocks for Masscan: {len(optimized_networks)}")
    logging.info(f"[*] Data saved to {output_file}.")

if __name__ == "__main__":
    asyncio.run(main())
