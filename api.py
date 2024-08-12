import asyncio
import os
import subprocess
from flask import Flask, request
from flask_restful import Resource, Api
from dotenv import load_dotenv
from fly_python_sdk.fly import Fly
import re


load_dotenv()

app = Flask(__name__)
api = Api(app)

fly = Fly(os.getenv("FLY_API_TOKEN"))


def update_fly_toml(new_app_name):
    with open("fly.toml", "r") as file:
        content = file.read()

    # Claude Powered regex
    updated_content = re.sub(
        r'^app\s=\s["\'].*["\']', f'app = "{new_app_name}"', content, flags=re.MULTILINE
    )

    with open("fly.toml", "w") as file:
        file.write(updated_content)


def deploy_to_fly(app_name):
    results = {}

    deploy_process = subprocess.Popen(
        f'fly deploy --app {app_name}',
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE,
        universal_newlines=True
    )
    deploy_stdout, deploy_stderr = deploy_process.communicate()
    results['deploy'] = (deploy_stdout, deploy_stderr, deploy_process.returncode)

    ipv4_process = subprocess.Popen(
        f'fly ips allocate-v4 --shared --app {app_name}',
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )
    ipv4_stdout, ipv4_stderr = ipv4_process.communicate()
    results['ipv4'] = (ipv4_stdout, ipv4_stderr, ipv4_process.returncode)

    ipv6_process = subprocess.Popen(
        f'fly ips allocate-v6 --app {app_name}',
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )
    ipv6_stdout, ipv6_stderr = ipv6_process.communicate()
    results['ipv6'] = (ipv6_stdout, ipv6_stderr, ipv6_process.returncode)

    return results


class FlyApp(Resource):
    async def create_fly_app(self, app_name):
        try:
            await fly.Org("personal").create_app(app_name=app_name)
            return True
        except Exception as e:
            print(f"Error creating app: {e}")
            return False
    
    async def delete_fly_app(self,app_name):
        try:
            await fly.Org("personal").App(app_name).delete()
            return True
        except Exception as e:
            print(f"Error deleting app: {e}")
            return False

    def post(self):
        app_name = request.json.get('app_name')
        if not app_name:
            return {"message": "app_name is required", "status": "error"}, 400

        success = asyncio.run(self.create_fly_app(app_name))
        if not success:
            return {"message": "Failed to create app", "status": "error"}, 500

        try:
            update_fly_toml(app_name)
        except Exception as e:
            return {"message": f"Error updating fly.toml: {str(e)}", "status": "error"}, 500

        try:
            deploy_results = deploy_to_fly(app_name)
            return {
                "message": f"App {app_name} created and deployed successfully",
                "status": "success",
                "deploy_output": deploy_results['deploy'][0],
                "ipv4_output": deploy_results['ipv4'][0],
                "ipv6_output": deploy_results['ipv6'][0]
            }, 201
        except Exception as e:
            return {"message": f"Deployment error: {str(e)}", "status": "error"}, 500

    def delete(self):
        app_name = request.json.get('app_name')
        if not app_name:
            return {"message": "app_name is required", "status": "error"}, 400

        success = asyncio.run(self.delete_fly_app(app_name))
        if not success:
            return {"message": "Failed to delete app", "status": "error"}, 500
        return {"message" : "App deleted", "status": "success" }


api.add_resource(FlyApp, "/api/apps")

if __name__ == "__main__":
    app.run(debug=True)
