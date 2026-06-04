<?php
namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Http;
use Log;
class SpeechController extends Controller
{
    public function generateSpeech(Request $request)
    {
        $request->validate([
            'text' => 'required|string',
        ]);

        $text = $request->input('text');
        $voiceId = config('services.elevenLabs.voice_id');
        $apiURL = "https://api.elevenlabs.io/v1/text-to-speech/{$voiceId}";
        $apiKey = config('services.elevenLabs.api_key');

        try {
            $response = Http::withHeaders([
                'xi-api-key' => $apiKey,
                'Content-Type' => 'application/json',
                'Accept' => 'audio/mpeg',
            ])->post($apiURL, [
                'text' => $text,
                'model_id' => 'eleven_monolingual_v1',
                'voice_settings' => [
                    'stability' => 0,
                    'similarity_boost' => 0,
                    'style' => 0,
                    'use_speaker_boost' => true,
                ],
            ]);

            if ($response->ok()) {
                return response($response->body())
                    ->header('Content-Type', 'audio/mpeg')
                    ->header('Content-Disposition', 'inline; filename="speech.mp3"');
            } else {
                return response()->json(['error' => 'Failed to generate speech'], $response->status());
            }
        } catch (\Exception $e) {
            return response()->json(['error' => 'An error occurred while generating speech'], 500);
        }
    }
}
