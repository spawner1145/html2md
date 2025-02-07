import httpx
import asyncio
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote, unquote

async def html_read(url):
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "Cache-Control": "max-age=0",
        "DNT": "1",
        "Priority": "u=0, i",
        "Referer": "https://github.com/",
        "Sec-Ch-Ua": "\"Not A(Brand\";v=\"8\", \"Chromium\";v=\"132\", \"Microsoft Edge\";v=\"132\"",
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": "\"Windows\"",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/132.0.0.0"
    }
    proxies = {"http://": "http://127.0.0.1:7890", "https://": "http://127.0.0.1:7890"}
    
    decoded_url = unquote(url)
    parsed_url = httpx.URL(decoded_url)
    encoded_path = quote(parsed_url.path)
    encoded_url = str(parsed_url.copy_with(path=encoded_path))
    
    async with httpx.AsyncClient(follow_redirects=True, timeout=None, proxies=proxies, headers=headers) as client:
        try:
            response = await client.get(encoded_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            if not soup.html:
                print("未找到<html>标签，请确认网页内容是否正确加载。")
                return
            
            for script_or_style in soup(['script', 'style']):
                script_or_style.decompose()

            url_attributes = {
                'a': 'href',
                'img': 'src',
                'link': 'href',
                'iframe': 'src',
            }

            def recurse(node, level=0):
                indent = '  ' * level
                result = []
                
                if hasattr(node, 'name') and node.name is not None:
                    tag_name = node.name.lower()
                    
                    if tag_name in ['script', 'style']:
                        return result
                    
                    if tag_name == 'pre' or tag_name == 'code':
                        all_lines = []
                        # 检查是否有直接的`<span>`子元素
                        spans = node.find_all('span', recursive=False)
                        if spans:
                            for span in spans:
                                # 获取每个span的所有子孙节点的文本，并保持其中的空白字符
                                line_parts = [part.get_text() if hasattr(part, "get_text") else str(part) for part in span.contents]
                                full_line = ''.join(line_parts)

                                # 如果行中只包含空白字符，也添加到all_lines中
                                stripped_line = full_line.strip()
                                if stripped_line or (full_line and not full_line.isspace()):
                                    all_lines.append(full_line)
                        else:
                            # 如果没有`<span>`子元素，则直接使用`<code>`标签内的文本，并保持其中的空白字符
                            code_text = node.get_text()
                            lines = code_text.split('\n')
                            for line in lines:
                                stripped_line = line.strip()
                                if stripped_line or (line and not line.isspace()):
                                    all_lines.append(line)

                        formatted_code = "\n".join([f"{indent}{line}" for line in all_lines])
                        result.append(f"{indent}```yaml\n{formatted_code}\n{indent}```")
                        return result
                    
                    if tag_name in url_attributes:
                        attr = url_attributes[tag_name]
                        url_attr_value = node.get(attr, '')
                        
                        if tag_name == 'a' and url_attr_value.lower().startswith('javascript:'):
                            return result
                        
                        full_url = urljoin(str(response.url), url_attr_value)
                        if tag_name == 'a':
                            img_tag = node.find('img')
                            if img_tag:
                                alt = img_tag.get('alt', 'No description')
                                result.append(f"{indent}[{alt}]({full_url})")
                            else:
                                link_text = ' '.join(node.stripped_strings)
                                result.append(f"{indent}[{link_text}]({full_url})")
                        elif tag_name == 'img':
                            alt = node.get('alt', 'No description')
                            result.append(f"{indent}[{alt}]({full_url})")
                        else:
                            result.append(f"{indent}[URL]({full_url})")
                    else:
                        for child in node.children:
                            result.extend(recurse(child, level + 1))
                elif isinstance(node, str) and node.strip():
                    text = node.strip()
                    if text and not text.startswith("//<![CDATA[") and not text.endswith("//]]>"):
                        result.append(f"{indent}{text}")
                
                return result

            extracted_info = recurse(soup.html.body if soup.html and soup.html.body else soup.html)
            return "\n".join(extracted_info)
        except httpx.RequestError as e:
            print(f"请求发生错误：{e}")
            return

async def main():
    while True:
        url = input("请输入要测试的URL（或输入'exit'退出）：")
        if url.lower() == 'exit':
            break
        try:
            print(await html_read(url))
        except Exception as e:
            print(f"发生错误：{e}")

if __name__ == "__main__":
    asyncio.run(main())
