import json
import re
from smolagents import GradioUI
from smolagents import stream_to_gradio


class TAGradioUI(GradioUI):

    def __init__(self, agent, blocks_init_args = {}, **kwargs):
        super().__init__(agent, **kwargs)
        self.blocks_init_args = blocks_init_args

    def create_app(self):
        import gradio as gr

        with gr.Blocks(theme="ocean", fill_height=True, **self.blocks_init_args) as app:
            # Add session state to store session-specific data
            session_state = gr.State({})
            stored_messages = gr.State([])
            file_uploads_log = gr.State([])

            with gr.Sidebar():
                gr.Markdown((
                    f"# {self.name.replace('_', ' ')}\n"
                    f"{self.description}"
                ))

                with gr.Group():
                    gr.Markdown("**Start here**", container=True)
                    text_input = gr.Textbox(
                        lines=3,
                        label="Chat Message",
                        container=False,
                        placeholder="Enter your prompt here and press Shift+Enter or press the button",
                    )
                    submit_btn = gr.Button("Submit", variant="primary")
                    # add examples here
                gr.Examples(
                    inputs=text_input,
                    examples=[
                        ["What is the MAC address of my interface?"],
                        ["Send an ethernet frame with random source and broadcast destination."],
                    ]
                )

                # If an upload folder is provided, enable the upload feature
                if self.file_upload_folder is not None:
                    upload_file = gr.File(label="Upload a file")
                    upload_status = gr.Textbox(label="Upload Status", interactive=False, visible=False)
                    upload_file.change(
                        self.upload_file,
                        [upload_file, file_uploads_log],
                        [upload_status, file_uploads_log],
                    )

                gr.Markdown('''
                    ## Powered by
                    - [llms](https://en.wikipedia.org/wiki/Large_language_model)
                    - [smolagents](https://github.com/huggingface/smolagents),
                    - [scapy](https://github.com/secdev/scapy)
                    - [gradio](https://gradio.app/)
                    - [freepik designs](https://www.freepik.com/)
                    ''')                 

            # Main chat interface
            chatbot = gr.Chatbot(
                label="Agent",
                type="messages",
                avatar_images=(
                    "assets/user_avatar.png",
                    "assets/agent_avatar.png",
                ),
                resizeable=True,
                scale=1,
                latex_delimiters=[
                    {"left": r"$$", "right": r"$$", "display": True},
                    {"left": r"$", "right": r"$", "display": False},
                    {"left": r"\[", "right": r"\]", "display": True},
                    {"left": r"\(", "right": r"\)", "display": False},
                ],
            )

            # Set up event handlers
            text_input.submit(
                self.log_user_message,
                [text_input, file_uploads_log],
                [stored_messages, text_input, submit_btn],
            ).then(self.interact_with_agent, [stored_messages, chatbot, session_state], [chatbot]).then(
                lambda: (
                    gr.Textbox(
                        interactive=True, placeholder="Enter your prompt here and press Shift+Enter or the button"
                    ),
                    gr.Button(interactive=True),
                ),
                None,
                [text_input, submit_btn],
            )

            submit_btn.click(
                self.log_user_message,
                [text_input, file_uploads_log],
                [stored_messages, text_input, submit_btn],
            ).then(self.interact_with_agent, [stored_messages, chatbot, session_state], [chatbot]).then(
                lambda: (
                    gr.Textbox(
                        interactive=True, placeholder="Enter your prompt here and press Shift+Enter or the button"
                    ),
                    gr.Button(interactive=True),
                ),
                None,
                [text_input, submit_btn],
            )

        return app
    def custom_msg_handler(self, msg):
        # if msg is json string, parse it
        if msg.content.startswith("{") and msg.content.endswith("}"):
            try:
                content_json = json.loads(msg.content)
                msg.content = content_json.get("thought", "")
            except json.JSONDecodeError:
                pass
        if "Execution Logs" in msg.metadata.get('title',''):
            msg.metadata['title'] = "Output"
            msg.content = re.sub(r'\nLast output from code snippet:', '', msg.content)

    def interact_with_agent(self, prompt, messages, session_state):
        import gradio as gr

        # Get the agent type from the template agent
        if "agent" not in session_state:
            session_state["agent"] = self.agent

        try:
            messages.append(gr.ChatMessage(role="user", content=prompt, metadata={"status": "done"}))
            yield messages

            for msg in stream_to_gradio(session_state["agent"], task=prompt, reset_agent_memory=False):
                if isinstance(msg, gr.ChatMessage):
                    messages[-1].metadata["status"] = "done"
                    self.custom_msg_handler(msg)
                    messages.append(msg)
                elif isinstance(msg, str):  # Then it's only a completion delta
                    msg = msg.replace("<", r"\<").replace(">", r"\>")  # HTML tags seem to break Gradio Chatbot
                    if messages[-1].metadata["status"] == "pending":
                        messages[-1].content = msg
                    else:
                        messages.append(gr.ChatMessage(role="assistant", content=msg, metadata={"status": "pending"}))
                yield messages

            yield messages
        except Exception as e:
            yield messages
            raise gr.Error(f"Error in interaction: {str(e)}")