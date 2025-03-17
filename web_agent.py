from flask import Flask, request, jsonify, render_template
from browser_use import Agent
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from openai import OpenAI
import asyncio
import os
import nest_asyncio
import re

# Load environment variables
load_dotenv()

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

app = Flask(__name__)

@app.route('/')
def index():
    # Render the index.html template
    return render_template('index.html')

@app.route('/api/browser-agent', methods=['POST'])
def run_browser_agent():
    try:
        # Get the prompt from the request
        data = request.json
        prompt = data.get('prompt')
        
        if not prompt:
            return jsonify({'error': 'No prompt provided'}), 400
        
        # Check if we're in Heroku environment
        is_heroku = os.environ.get('DYNO') is not None
        
        # If on Heroku, use direct GPT instead of browser
        if is_heroku:
            # Use GPT to simulate browser results
            enhanced_result = simulate_browser_with_gpt(prompt)
            return jsonify({'result': enhanced_result})
        else:
            # Execute the browser agent task (for local development)
            result_obj = asyncio.run(execute_agent(prompt))
            
            # Extract the final result text
            raw_result = extract_result_text(result_obj)
            
            # Post-process with GPT to make it more human-friendly
            enhanced_result = enhance_with_gpt(prompt, raw_result)
            
            # Return the formatted result as JSON
            return jsonify({'result': enhanced_result})
    
    except Exception as e:
        # Log the full error for debugging
        import traceback
        print(f"Error in browser agent: {str(e)}")
        print(traceback.format_exc())
        
        # Return a 500 error with details
        return jsonify({'error': f'Server error: {str(e)}'}), 500

def simulate_browser_with_gpt(prompt):
    """
    Use GPT to simulate browser agent results directly, without attempting browser automation.
    This is used in Heroku environment where browser initialization fails.
    """
    try:
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        
        system_prompt = """
        You are a web browser agent that can execute searches and extract information from the web.
        For this task, you'll need to simulate the results without actually browsing the web.
        
        When provided with a search prompt:
        1. Explain how you would approach the search task step-by-step
        2. Provide realistic, current information as if you browsed the web
        3. For flights, prices, or comparisons, generate plausible example data
        4. Format your response with HTML and emojis for better presentation
        5. Structure your response as if it was real search results
        
        Be honest that these are simulated results. For example, for flights, you can say:
        "Based on typical pricing patterns, here are the likely cheapest flights:"
        
        Use <div>, <h3>, <p>, <ul>, <li>, <strong> and other HTML tags to improve readability.
        """
        
        user_content = f"""
        Execute the following browser agent task and provide realistic results:
        
        {prompt}
        """
        
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]
        )
        
        return completion.choices[0].message.content
    
    except Exception as e:
        print(f"Error simulating browser with GPT: {str(e)}")
        return f"<div class='error-message'><p>Sorry, I encountered an error while processing your request: {str(e)}</p></div>"

def extract_result_text(result_obj):
    """
    Extract the human-readable result from the agent's response object.
    This function handles different object structures that might be returned.
    """
    # Convert the result to a string for easier processing
    result_str = str(result_obj)
    
    # First, try to extract the 'done' text, which is usually the final result
    done_match = re.search(r"ActionResult\(is_done=True, success=True, extracted_content=['\"](.+?)['\"]", result_str)
    if done_match:
        return done_match.group(1)
    
    # Look for specific result patterns
    result_patterns = [
        r"Result: (.+?)(?=INFO)",  # Match text after "Result:" until "INFO"
        r"Successfully found (.+?)(?=INFO)",  # Match text after "Successfully found" until "INFO"
        r"The 3 cheapest (.+?)(?=INFO)"  # Match text after "The 3 cheapest" until "INFO"
    ]
    
    for pattern in result_patterns:
        match = re.search(pattern, result_str, re.DOTALL)
        if match:
            return match.group(1).strip()
    
    # If we still haven't found anything useful, check if there are any JSON-like extractions
    extractions = re.findall(r'Extracted from page[\s\S]*?```json([\s\S]*?)```', result_str)
    if extractions:
        # Get the last extraction
        last_extraction = extractions[-1]
        return f"Raw data extracted: {last_extraction}"
    
    # If all else fails, return a generic message
    return "Task completed. The browser agent executed the search but couldn't format a clean result."

def enhance_with_gpt(original_prompt, raw_result):
    """
    Use GPT to enhance the raw result into a more human-friendly format with emojis.
    """
    try:
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        
        system_prompt = """
        You are a helpful assistant that formats search results into a user-friendly, visually appealing format.
        Your task is to:
        1. Take the raw results from a browser search agent
        2. Format them in a clear, organized way
        3. Add relevant emojis to make the content more engaging
        4. Use HTML formatting for better presentation
        5. Make the information easy to scan and understand
        6. Maintain all the factual information from the original results
        
        Use <div>, <h3>, <p>, <ul>, <li>, <strong> and other HTML tags to improve readability.
        Highlight key information like prices, dates, and important details.
        """
        
        user_content = f"""
        Original search prompt: {original_prompt}
        
        Raw results:
        {raw_result}
        
        Please format this into a user-friendly display with appropriate emojis and HTML formatting.
        """
        
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]
        )
        
        enhanced_result = completion.choices[0].message.content
        return enhanced_result
    
    except Exception as e:
        print(f"Error enhancing with GPT: {str(e)}")
        # If there's an error with GPT, return the original result
        return raw_result

async def execute_agent(task):
    """Execute the browser agent with the given task."""
    try:
        # Initialize the language model
        llm = ChatOpenAI(model="gpt-4o")
        
        # Create and run the agent with proper headless configuration
        agent = Agent(
            task=task,
            llm=llm,
            headless=True,  # Ensure headless mode is explicitly enabled
            launch_options={
                "chromium_sandbox": False,  # Disable sandbox for containerized environments
                "args": [
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-software-rasterizer",
                    "--disable-extensions"
                ]
            }
        )
        
        # Execute the agent and get the result
        result = await agent.run()
        
        # For debugging
        print(f"Agent result type: {type(result)}")
        
        # Return the result
        return result
    
    except Exception as e:
        # Re-raise the exception to be caught by the outer handler
        raise Exception(f"Failed to execute agent: {str(e)}")

if __name__ == '__main__':
    # Get port from environment variable or use 8000 as default
    port = int(os.environ.get('PORT', 8000))
    # In production (like on Heroku), don't use debug mode
    debug_mode = os.environ.get('DYNO') is None
    app.run(host='0.0.0.0', port=port, debug=debug_mode)