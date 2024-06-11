<script>
	import CodeEditor from '$lib/components/common/CodeEditor.svelte';

	export let value = '';

	let codeEditor;

	let boilerplate = `# Tip: Use Ctrl/Cmd + S to format the code

from datetime import datetime
import requests


class Tools:
    def __init__(self):
        pass

    # Add your custom tools using pure Python code here, make sure to add type hints
    # Use Sphinx-style docstrings to document your tools, they will be used for generating tools specifications
    # Please refer to function_calling_filter_pipeline.py file from pipelines project for an example

    def get_current_time(self) -> str:
        """
        Get the current time.
        :return: The current time.
        """

        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")
        return f"Current Time = {current_time}"

    def calculator(self, equation: str) -> str:
        """
        Calculate the result of an equation.
        :param equation: The equation to calculate.
        """

        # Avoid using eval in production code
        # https://nedbatchelder.com/blog/201206/eval_really_is_dangerous.html
        try:
            result = eval(equation)
            return f"{equation} = {result}"
        except Exception as e:
            print(e)
            return "Invalid equation"

`;

	export const submitHandler = async () => {
		if (codeEditor) {
			codeEditor.formatPythonCodeHandler();
		}
	};
</script>

<CodeEditor bind:value {boilerplate} bind:this={codeEditor} />
