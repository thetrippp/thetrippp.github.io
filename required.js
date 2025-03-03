/*function copyCode() {
    const codeElement = document.querySelector("#code-block code");
    const codeText = Array.from(codeElement.querySelectorAll("span"))
        .map(span => span.innerText)
        .join("\n");
    navigator.clipboard.writeText(codeText).then(() => {
        alert("Code copied to clipboard!");
    });
}
*/

function copyCode() {
    const codeBlock = document.getElementById('code-block');
    const range = document.createRange();
    range.selectNode(codeBlock);
    window.getSelection().removeAllRanges();
    window.getSelection().addRange(range);
  
    try {
      // Copy the selected text to clipboard
      document.execCommand('copy');
      alert('Code copied to clipboard!');
    } catch (err) {
      alert('Failed to copy code');
    }
  
    // Clear selection
    window.getSelection().removeAllRanges();
  }
