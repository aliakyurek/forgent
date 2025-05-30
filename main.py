import os
import yaml
import json
from scapy.all import show_interfaces, dev_from_index, get_if_list, conf
import importlib
import sys

from dotenv import load_dotenv
from smolagents import CodeAgent, LiteLLMModel
import gradio.themes as themes
from lib import TAGradioUI

_ = load_dotenv()

with open("theme.json", "r") as f:
    theme_dict = json.load(f)

theme = themes.ThemeClass.from_dict(theme_dict)
theme.block_label_text_color_dark = "#00cccc"
theme.spacing_size = "sm"
theme.input_padding = "5px" 

BLOCKS_INIT_ARGS = {
    "title": "Forgent",
    "css": "a { text-decoration: none; }",
    "js": """
        () => {
            document.body.classList.toggle('dark');
        }""",
    "analytics_enabled": False
}

BLOCKS_LAUNCH_ARGS = {
    "favicon_path": "favicon.png",
    "share": False,
    "inbrowser": True,
    "show_api": False,
}

def main():
    # Check for raw socket capability (root/admin privileges)
    try:
        # Try to open a raw socket using scapy's conf.L3socket
        s = conf.L3socket()
        s.close()
    except Exception as e:
        print("Error: Insufficient privileges to use raw sockets.Please run as administrator/root.")
        sys.exit(1)

    # list the interfaces
    show_interfaces()
    interface_index = 0
    # ask user to select an interface
    while not interface_index:
        interface_index = input("Select the interface index: ")
        # validate the input
        try:
            interface_index = int(interface_index)
            if interface_index < 0 or interface_index >= len(get_if_list()):
                print("Invalid index. Please try again.")
                interface_index = 0
        except ValueError:
            print("Invalid index. Please try again.")
            interface_index = 0

    with open('settings.yaml', 'r') as file:
        settings = yaml.safe_load(file)
    
    model = LiteLLMModel(
        api_key=os.getenv("API_KEY"),
        **settings['LiteLLMModel']
    )            

    # get the original prompts from the package
    default_prompts = yaml.safe_load(importlib.resources.files("smolagents.prompts").joinpath("code_agent.yaml").read_text())

    # replace the prompts with the4 custom ones
    with open('prompts.yaml', 'r') as file:
        custom_prompts = yaml.safe_load(file)

    custom_prompts["system_prompt"] = custom_prompts["system_prompt"].replace("%%INTERFACE%%",dev_from_index(interface_index).name)
    default_prompts.update(custom_prompts)

    agent = CodeAgent(tools=[], model=model, add_base_tools=True, additional_authorized_imports=["scapy.all","socket"], 
                      prompt_templates=default_prompts, name="Forgent", description="Forges 🛠️ and sends packets over layer 2 and layer 3, captures and analyzes packets, and provides network information.",
                      use_structured_outputs_internally=True)

    TAGradioUI(agent, blocks_init_args=BLOCKS_INIT_ARGS).launch(**BLOCKS_LAUNCH_ARGS)

if __name__ == "__main__":
    main()
