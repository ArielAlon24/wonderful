# Wonderful

## phase 1

I started by creating a function that trasncribes audio files using Whisper's api (https://github.com/openai/whisper), after loading the base model, I exprimented with it's transcribe function which returns:

return dict(
    text=tokenizer.decode(all_tokens[len(initial_prompt_tokens) :]),
    segments=all_segments,
    language=language,
)

the goal is to parse this result into an .srt file, which lead me to this site:

https://docs.fileformat.com/video/srt/

After creating a class for the transcriber and understading, the .srt syntax I created my own transcribe function and used https://validator.subtitledpro.com/ to verify if it works correctly. In the process I found out that each subtitle id needs to be positive, and that's why every id is incremented by 1.

Now after the transcriber works correctly I've started looking into the best way to work with files in FastAPI which lead me to this article:

https://fastapi.tiangolo.com/tutorial/request-files/

This work made me dig up the whisper api, which to my suprise already included a writer for .srt files.

It's time for the server - as the assigment said, I used FastAPI with two routes, one for uploading a file for transcription and for getting the result,


