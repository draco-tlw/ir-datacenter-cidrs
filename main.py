import asyncio
import aiohttp
import ipaddress
import logging
import sys

logging.basicConfig(level=logging.INFO, format='%(message)s')

async def get_iran_asns(session):
    url = "https://stat.ripe.net/data/country-asns/data.json?resource=IR"
    logging.info("[*] Fetching dynamic ASN list for Iran (IR)...")
    
    try:
        async with session.get(url, timeout=20) as response:
            if response.status == 200:
                data = await response.json()
                countries = data.get('data', {}).get('countries', [])
                if countries:
                    routed_asns = countries[0].get('routed', [])
                    logging.info(f"[+] Successfully fetched {len(routed_asns)} active ASNs for Iran.")
                    return routed_asns
            else:
                logging.error(f"[-] Failed to fetch ASN list. HTTP Status: {response.status}")
    except Exception as e:
        logging.error(f"[-] Network error while fetching ASNs: {e}")
        
    return []

async def fetch_cidr(session, asn, semaphore, retries=4):
    url = f"https://stat.ripe.net/data/announced-prefixes/data.json?resource=AS{asn}"
    
    async with semaphore:
        for attempt in range(retries):
            try:
                async with session.get(url, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        prefixes = [item['prefix'] for item in data['data']['prefixes']]
                        return asn, prefixes
                        
                    elif response.status == 429: # RIPE Rate Limit Hit
                        wait_time = (2 ** attempt) + 2
                        await asyncio.sleep(wait_time)
                    else:
                        await asyncio.sleep(2)
                        
            except (aiohttp.ClientError, asyncio.TimeoutError):
                await asyncio.sleep(2)
                
        return asn, []

async def main():
    print("=" * 65)
    print("\033[1;96m[*] Riftway - Dynamic Country-Wide CIDR Extractor (Optimized)\033[0m")
    print("=" * 65)
    
    raw_cidrs_set = set()
    
    connector = aiohttp.TCPConnector(limit=25, keepalive_timeout=30, ttl_dns_cache=300)
    semaphore = asyncio.Semaphore(15) 
    
    async with aiohttp.ClientSession(connector=connector) as session:
        target_asns = await get_iran_asns(session)
        if not target_asns:
            logging.error("\033[91m[!] Exiting: No ASNs retrieved. Check your connection to ripe.net.\033[0m")
            sys.exit(1)
            
        logging.info("\n[*] Phase 1: Initiating High-Speed BGP Prefix Extraction...")
        
        tasks = [fetch_cidr(session, asn, semaphore) for asn in target_asns]
        total_asns = len(target_asns)
        completed = 0
        failed_asns = 0
        
        for future in asyncio.as_completed(tasks):
            asn, cidrs = await future
            completed += 1
            
            if not cidrs:
                failed_asns += 1
            
            valid_ipv4_count = 0
            for cidr in cidrs:
                if ':' not in cidr: 
                    raw_cidrs_set.add(cidr)
                    valid_ipv4_count += 1
            
            sys.stdout.write(f"\r\033[K[>] Progress: {completed}/{total_asns} ASNs processed. Latest: AS{asn:<6} ({valid_ipv4_count} IPv4)")
            sys.stdout.flush()

    print("\n")
    logging.info("-" * 65)
    if failed_asns > 0:
        logging.warning(f"\033[93m[!] Warning: {failed_asns} ASNs failed to respond. They were skipped.\033[0m")
        
    logging.info("[*] Phase 2: Compiling and collapsing overlapping subnets...")
    
    raw_networks = [ipaddress.ip_network(cidr, strict=False) for cidr in raw_cidrs_set]
    optimized_networks = list(ipaddress.collapse_addresses(raw_networks))
    
    output_file = "iran_dynamic_cidrs.txt"
    with open(output_file, "w") as f:
        for net in optimized_networks:
            f.write(str(net) + "\n")
            
    logging.info("=" * 65)
    logging.info(f"\033[1;92m[+] Database Successfully Compiled!\033[0m")
    logging.info(f"[*] Total Active ASNs      : {len(target_asns)}")
    logging.info(f"[*] Unique IPv4 Strings    : {len(raw_cidrs_set):,}")
    logging.info(f"[*] Optimized/Merged CIDRs : {len(optimized_networks):,}")
    logging.info(f"[*] Final Output File      : '{output_file}'")
    logging.info("=" * 65)

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\033[91m[!] Process immediately halted by user (Ctrl+C).\033[0m")
        sys.exit(0)
