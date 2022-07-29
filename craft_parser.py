from bs4 import BeautifulSoup as BS
from aiohttp import ClientSession
from alive_progress import alive_it

import os, asyncio

from config import headers, category


class WallpaperCraftParser:
    '''Downloading images by category from "https://wallpaperscraft.ru" '''
    __slots__ = ('__headers', '__category', 'proxy_list', '__select_category')

    def __init__(self) -> None:
        self.__headers = headers
        self.__category = category
        self.__select_category = self.__ask()
        with open(f'{os.getcwd()}\\ok_proxy.txt') as f:
            self.proxy_list = f.read().split('\n')

    def __ask(self):
        select_category = ''
        [print(key) for key in self.__category]
        while True:
            ask = input('Enter the name category: ').strip().lower()
            
            if ask in self.__category:
                select_category = self.__category[ask]
                break
            else:
                print('Enter category name or all')

        return select_category

    def __rotate_proxy(self, proxy):
        '''Proxy rotator'''
        return self.proxy_list[0] if proxy == self.proxy_list[-1] else self.proxy_list[self.proxy_list.index(proxy) + 1]

    async def _get_page_source(self, url, session):
        '''Getting data from page using proxy'''
        max_retrying = 0
        proxy = self.proxy_list[0]
        while max_retrying < len(self.proxy_list)*10:
            try:
                async with session.get(url, proxy=proxy, timeout=10) as response:
                    if response.status == 200:
                        return await response.read()
                    break
            except:
                max_retrying += 1
                await asyncio.sleep(1.5)
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        return await response.read()
                proxy = self.__rotate_proxy(proxy)

        raise TimeoutError('All proxy are deprecated')

    async def __collect_tasks(self, urls, session):
        '''Collect tasks and return sequence'''
        tasks = (asyncio.create_task(self._get_page_source(url, session)) for url in urls)
        return await asyncio.gather(*tasks)

    async def collect_data(self, urls):
        async with ClientSession(headers=self.__headers) as session:
            return await self.__collect_tasks(urls, session)

    async def __page_pagination(self):
        response = await self.collect_data(urls=[f'https://wallpaperscraft.ru{self.__select_category}'])
        soup = BS(response[0], 'lxml')
        pagination = int(soup.select('li[class="pager__item pager__item_last-page"] a.pager__link')[-1].get('href').split('/')[-1].replace('page', ''))

        return (f'https://wallpaperscraft.ru{self.__select_category}/page{page}' for page in range(1, pagination + 1))

    async def get_referer_links(self):
        '''Returns links to cards'''
        links = await self.__page_pagination()
        links_response = await self.collect_data(links)
        unpack_response = set() 
        for response in links_response:
            soup = BS(response, 'lxml')
            items = soup.select('ul.wallpapers__list a.wallpapers__link')
            if items: 
                for item in items:
                    unpack_response.add('https://wallpaperscraft.ru' + item.get('href'))
                
        return unpack_response

    async def get_image_link(self):
        '''Take the link formed by the button on the original resolution and return it'''
        links = await self.get_referer_links()
        links_response = await self.collect_data(links)
        image_links = set()
        for response in alive_it(links_response):
            soup = BS(response, 'lxml')
            link = soup.select_one('a.wallpaper__button.gui-button.gui-button_full.gui-visible-mobile')
            if link: image_links.add('https://wallpaperscraft.ru' + link.get('href'))

        return image_links

    async def get_download_links(self):
        '''Get download links from referer links'''
        links = await self.get_image_link()
        links_response = await self.collect_data(links)
        download_links = set()
        for response in alive_it(links_response):
            soup = BS(response, 'lxml')    
            download_link = soup.select('div.wallpaper__placeholder > a > img')
            if download_link: download_links.add(download_link[0].get('src'))
       
        return download_links

    async def download(self):
        '''Save gotten bytes as image file'''
        links = await self.get_download_links()
        names = (link.split('/')[-1] for link in links)
        links_response = await self.collect_data(links)
        print('Downloading...')
        for response, name in zip(links_response, names):
            with open(f'{os.getcwd()}\\craft_image\\{name}', 'wb') as file:
                file.write(response)

if __name__ == '__main__':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(WallpaperCraftParser().download())