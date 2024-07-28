#!/usr/bin/env python
# coding:utf-8
import os
import requests,json
from requests_toolbelt import MultipartEncoder

class Gitee:
    def __init__(self, owner, token):
        self.owner = owner
        self.token = token
        
    def create_release(self, repo, tag_name, name, body = '-', target_commitish = 'master'):
        url = f'https://gitee.com/api/v5/repos/{self.owner}/{repo}/releases'
        data = {
            'access_token': self.token,
            'tag_name': tag_name,
            'name': name,
            'body': body,
            'target_commitish': target_commitish,
        }
        response = requests.post(url, data=data)
        res = response.json() 
        if response.status_code < 200 or response.status_code > 300:
            return False, res["message"] if "message" in res else f"Response status_code is {response.status_code}"
        
        if "id" in res:
            return True, res["id"]
        else:
            return False, "No 'id' in response"
            
    def upload_asset(self, repo, release_id, files = None, file_name = None, file_path = None):
        if files:
            fields = [('access_token', self.token)]
            idx = 1
            for file_path in files:
                file_path = file_path.strip()
                if not os.path.isfile(file_path):
                    raise ValueError('file_path not exists: ' + file_path)
                file = ('file', (os.path.basename(file_path), open(file_path, 'rb'), 'application/octet-stream'))
                idx = idx + 1
                fields.append(file)
        elif file_name and file_path:
            fields = {
                'access_token': self.token,
                'file': (file_name, open(file_path, 'rb'), 'application/octet-stream'),
            }
        else:
            raise ValueError('files or (file_name and file_path) should not be False at the same time')
        m = MultipartEncoder(fields=fields)
        url = f"https://gitee.com/api/v5/repos/{self.owner}/{repo}/releases/{release_id}/attach_files"
        response = requests.post(url, data=m, headers={'Content-Type': m.content_type})
        # print(response.text)
        res = response.json()
        if response.status_code < 200 or response.status_code > 300:
            return False, res["message"] if "message" in res else f"Response status_code is {response.status_code}"
        
        if "browser_download_url" in res:
            return True, res["browser_download_url"]
        else:
            return False, "No 'browser_download_url' in response"

def get(key):
    val = os.environ.get(key)
    if not val:
        raise ValueError(f'{key} not set in the environment')
    return val
    
def set_result(name, result):
    print("result: ", f"{name}={result}")
    github_out = os.environ.get("GITHUB_OUTPUT")
    if github_out:
        with open(github_out, 'a', encoding='utf-8') as output:
            if not '\n' in result:
                output.write(f"{name}={result}\n")
                print(f"{name}={result}\n")
            else:
                delimiter = 'EOF'
                output.write(f"{name}<<{delimiter}\n{result}\n{delimiter}\n")
                print(f"{name}<<{delimiter}\n{result}\n{delimiter}\n")
                
def create_release():
    gitee_owner = get('gitee_owner')
    gitee_token = get('gitee_token')
    gitee_repo = get('gitee_repo')
    gitee_tag_name = get('gitee_tag_name')
    gitee_release_name = get('gitee_release_name')
    gitee_release_body = get('gitee_release_body')
    gitee_target_commitish = get('gitee_target_commitish')
    
    gitee_files = os.environ.get('gitee_files')
    if gitee_files:
        gitee_files = gitee_files.strip().split("\n")
    else:
        gitee_file_name = os.environ.get('gitee_file_name')
        gitee_file_path = os.environ.get('gitee_file_path')
        if (gitee_file_name and not gitee_file_path) or (gitee_file_path and not gitee_file_name):
            raise ValueError('gitee_file_name and gitee_file_path should be set together')
        if gitee_file_path and not os.path.isfile(gitee_file_path):
            raise ValueError('gitee_file_path not exists: ' + gitee_file_path)
    
    gitee_client = Gitee(owner = gitee_owner, token = gitee_token)
    success, release_id = gitee_client.create_release(repo = gitee_repo, tag_name = gitee_tag_name, name = gitee_release_name, 
                body = gitee_release_body, target_commitish = gitee_target_commitish)
    if success:
        print(release_id)
        if gitee_files:
            for file_path in gitee_files:
                file_path = file_path.strip()
                if not os.path.isfile(file_path):
                    raise ValueError('file_path not exists: ' + file_path)
                success, msg = gitee_client.upload_asset(gitee_repo, release_id, file_name = os.path.basename(file_path), file_path = file_path)
                if not success:
                    raise Exception("Upload file asset failed: " + msg)
        elif gitee_file_path:
            success, msg = gitee_client.upload_asset(gitee_repo, release_id, file_name = gitee_file_name, file_path = gitee_file_path)
            if not success:
                raise Exception("Upload file asset failed: " + msg)
        set_result("release-id", release_id)
    else:
        raise Exception("Create release failed: " + release_id)

def upload_asset():
    gitee_release_id = get('gitee_release_id')
    gitee_owner = get('gitee_owner')
    gitee_repo = get('gitee_repo')
    gitee_token = get('gitee_token')
        
    gitee_files = os.environ.get('gitee_files')
    
    gitee_client = Gitee(owner = gitee_owner, token = gitee_token)
    if gitee_files:
        result = []
        gitee_files = gitee_files.strip().split("\n")
        for file_path in gitee_files:
            file_path = file_path.strip()
            if not os.path.isfile(file_path):
                raise ValueError('file_path not exists: ' + file_path)
            success, msg = gitee_client.upload_asset(gitee_repo, gitee_release_id, file_name = os.path.basename(file_path), file_path = file_path)
            if not success:
                raise Exception("Upload file asset failed: " + msg)
            result.append(msg)
        set_result("download-url", '\n'.join(result))
    else:
        gitee_file_name = get('gitee_file_name')
        gitee_file_path = get('gitee_file_path')
        if gitee_file_path and not os.path.isfile(gitee_file_path):
            raise ValueError('gitee_file_path not exists: ' + gitee_file_path)
        success, msg = gitee_client.upload_asset(gitee_repo, gitee_release_id, file_name = gitee_file_name, file_path = gitee_file_path)
        if not success:
            raise Exception("Upload file asset failed: " + msg)
        set_result("download-url", msg)
        
if __name__ == "__main__":
    gitee_release_id = os.environ.get("gitee_release_id")
    # print("gitee_release_id: ", gitee_release_id)
    if gitee_release_id:
        upload_asset()
    else:
        create_release()
