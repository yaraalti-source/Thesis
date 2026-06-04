<?php

namespace App\Http\Controllers;

use App\Models\Translation;
use Auth;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Storage;
use Log;

class TranslationController extends Controller
{
    /**
     * Display a listing of the resource.
     */
    public function index()
    {
        $translations = Translation::all();
        return response()->json($translations);
    }

    /**
     * Store a newly created resource in storage.
     */
    public function store(Request $request)
    {
        try {
            // Log the request for debugging
            Log::info('=== STORE REQUEST RECEIVED ===', [
                'method' => $request->method(),
                'url' => $request->fullUrl(),
                'has_files' => $request->hasFile('input_data') || $request->hasFile('translated_audio'),
                'all_fields' => $request->all(),
                'input_type' => $request->input('input_type'),
                'translated_text' => $request->input('translated_text'),
                'headers' => $request->headers->all(),
            ]);
        
            // Get the authenticated user first
            $user = Auth::user();
            
            if (!$user) {
                Log::error('No authenticated user in store method');
                return response()->json(['error' => 'Unauthorized'], 401);
            }
            
            Log::info('User authenticated for store', ['user_id' => $user->id, 'email' => $user->email]);
        
            // Validate incoming request
            // Note: For live translations, input_data and translated_audio are optional
            // Testing mode: Very high limit (1000MB = 1000000 KB) to allow large video files
            $validatedData = $request->validate([
                'input_type' => 'required|in:video,image,live',
                'translated_text' => 'required|string',
                'translated_audio' => 'nullable|file|mimes:mp3,wav',
                'input_data' => 'nullable|file|mimes:mp4,jpg,jpeg,png|max:1000000',
            ]);
            
            // For live translations without files, input_data can be null
            // This allows saving live translations directly to history
    
            // Save the input file and get the path
            $inputDataPath = null;
            if ($request->hasFile('input_data')) {
                try {
                    $file = $request->file('input_data');
                    $fileSize = $file->getSize(); // Size in bytes
                    $fileSizeMB = round($fileSize / 1024 / 1024, 2);
                    
                    Log::info('Input file received', [
                        'name' => $file->getClientOriginalName(),
                        'size' => $fileSizeMB . ' MB',
                        'mime' => $file->getMimeType(),
                        'input_type' => $validatedData['input_type']
                    ]);
                    
                    $inputDataPath = $file->store('uploads/input_data', 'public');
                    Log::info('Input file saved successfully', [
                        'path' => $inputDataPath,
                        'size' => $fileSizeMB . ' MB'
                    ]);
                } catch (\Exception $e) {
                    Log::error('Error saving input file', [
                        'error' => $e->getMessage(),
                        'trace' => $e->getTraceAsString()
                    ]);
                    // Continue without file - translation can still be saved
                }
            } else {
                Log::info('No input_data file provided');
            }
        
            // Save the translated audio file and get the path
            $translatedAudioPath = null;
            if ($request->hasFile('translated_audio')) {
                $translatedAudioPath = $request->file('translated_audio')->store('uploads/translated_audio', 'public');
                Log::info('Audio file saved', ['path' => $translatedAudioPath]);
            } else {
                Log::info('No translated_audio file provided');
            }
        
            // Create a new translation entry in the database
            $translation = Translation::create([
                'user_id' => $user->id,
                'input_type' => $validatedData['input_type'],
                'input_data' => $inputDataPath,
            ]);
            
            Log::info('Translation record created', [
                'id' => $translation->id,
                'user_id' => $translation->user_id,
                'input_type' => $translation->input_type,
            ]);
    
            // Save the translated text in the `translated_text` table
            $translatedText = $translation->translatedText()->create([
                'text' => $validatedData['translated_text'],
            ]);
            
            Log::info('Translated text saved', [
                'translation_id' => $translation->id,
                'text_length' => strlen($validatedData['translated_text']),
            ]);
    
            // Save the translated audio path in the `translated_audio` table (if present)
            if ($translatedAudioPath) {
                $translation->translatedAudio()->create([
                    'audio_path' => $translatedAudioPath,
                ]);
                Log::info('Translated audio saved', ['translation_id' => $translation->id]);
            }
    
            Log::info('Translation saved successfully', [
                'translation_id' => $translation->id,
                'user_id' => $translation->user_id,
            ]);
        
            // Return a success response
            return response()->json([
                'success' => true,
                'message' => 'Translation saved successfully',
                'translation' => $translation
            ], 201);
        } catch (\Illuminate\Validation\ValidationException $e) {
            Log::error('Validation error in store', ['errors' => $e->errors()]);
            return response()->json(['error' => 'Validation failed', 'errors' => $e->errors()], 422);
        } catch (\Exception $e) {
            Log::error('Error saving translation', [
                'error' => $e->getMessage(),
                'trace' => $e->getTraceAsString()
            ]);
            return response()->json(['error' => 'Failed to save translation', 'message' => $e->getMessage()], 500);
        }
    }
    
    /**
     * Get all translations for the authenticated user.
     */
    public function getUserTranslations(Request $request)
{
    try {
        // Try to get user with explicit guard
        $user = Auth::guard('api')->user();
        
        if (!$user) {
            \Log::error('No authenticated user found in show method', [
                'token_present' => $request->bearerToken() ? 'yes' : 'no',
                'headers' => $request->headers->all()
            ]);
            return response()->json(['error' => 'Unauthorized', 'message' => 'User not authenticated'], 401);
        }

        \Log::info('Fetching translations for User ID:', ['id' => $user->id, 'email' => $user->email]);

        // First, check if there are ANY translations in the database (for debugging)
        $allTranslationsCount = Translation::count();
        $userTranslationsCount = Translation::where('user_id', $user->id)->count();
        $nullUserTranslationsCount = Translation::whereNull('user_id')->count();
        
        \Log::info('Translation counts:', [
            'total' => $allTranslationsCount,
            'for_user' => $userTranslationsCount,
            'null_user_id' => $nullUserTranslationsCount,
            'user_id' => $user->id
        ]);

        // Load translations along with related translated text and audio
        $translations = Translation::with(['translatedText', 'translatedAudio'])
                        ->where('user_id', $user->id)
                        ->orderBy('created_at', 'desc')
                        ->get();

        \Log::info('Translations query result:', [
            'count' => $translations->count(),
            'raw_translations' => $translations->map(function($t) {
                return [
                    'id' => $t->id,
                    'user_id' => $t->user_id,
                    'input_type' => $t->input_type,
                    'has_translated_text' => $t->translatedText ? 'yes' : 'no',
                    'has_translated_audio' => $t->translatedAudio ? 'yes' : 'no',
                ];
            })->toArray()
        ]);

        // Return empty array if no translations found (frontend expects array, not 404)
        if ($translations->isEmpty()) {
            \Log::warning('No translations found for user', ['user_id' => $user->id]);
            return response()->json([]);
        }

        // Transform the translations to include only the required fields
        $response = $translations->map(function ($translation) {
            try {
                // Get the full URL for input_data if it exists
                $inputDataUrl = null;
                if ($translation->input_data) {
                    try {
                        // Use Storage::url() which returns the correct path format
                        // This returns something like "/storage/uploads/input_data/filename.mp4"
                        $relativeUrl = Storage::disk('public')->url($translation->input_data);
                        
                        // Build absolute URL using APP_URL
                        $baseUrl = rtrim(config('app.url'), '/');
                        // Storage::url() already includes leading slash, so just concatenate
                        $inputDataUrl = $baseUrl . $relativeUrl;
                        
                        \Log::info('Video URL constructed', [
                            'path' => $translation->input_data,
                            'storage_url' => $relativeUrl,
                            'full_url' => $inputDataUrl,
                            'app_url' => config('app.url'),
                            'translation_id' => $translation->id
                        ]);
                    } catch (\Exception $e) {
                        \Log::error('Error constructing video URL', [
                            'path' => $translation->input_data,
                            'error' => $e->getMessage(),
                            'translation_id' => $translation->id
                        ]);
                        // Still try to construct a URL even if file check fails
                        $baseUrl = rtrim(config('app.url'), '/');
                        $storagePath = ltrim($translation->input_data, '/');
                        $inputDataUrl = $baseUrl . '/storage/' . $storagePath;
                    }
                }
                
                // Get the full URL for translated_audio if it exists
                $translatedAudioUrl = null;
                if ($translation->translatedAudio && $translation->translatedAudio->audio_path) {
                    try {
                        // Use Storage::url() which returns the correct path format
                        $relativeUrl = Storage::disk('public')->url($translation->translatedAudio->audio_path);
                        
                        // Build absolute URL using APP_URL
                        $baseUrl = rtrim(config('app.url'), '/');
                        $translatedAudioUrl = $baseUrl . $relativeUrl;
                        
                        \Log::info('Audio URL constructed', [
                            'path' => $translation->translatedAudio->audio_path,
                            'storage_url' => $relativeUrl,
                            'full_url' => $translatedAudioUrl,
                            'translation_id' => $translation->id
                        ]);
                    } catch (\Exception $e) {
                        \Log::error('Error constructing audio URL', [
                            'path' => $translation->translatedAudio->audio_path,
                            'error' => $e->getMessage(),
                            'translation_id' => $translation->id
                        ]);
                        // Still try to construct a URL even if file check fails
                        $baseUrl = rtrim(config('app.url'), '/');
                        $storagePath = ltrim($translation->translatedAudio->audio_path, '/');
                        $translatedAudioUrl = $baseUrl . '/storage/' . $storagePath;
                    }
                }
                
                $result = [
                    'id' => $translation->id,
                    'input_type' => $translation->input_type,
                    'input_data' => $inputDataUrl,
                    'translated_text' => $translation->translatedText ? $translation->translatedText->text : '',
                    'translated_audio' => $translatedAudioUrl,
                    'created_at' => $translation->created_at ? $translation->created_at->toIso8601String() : null,
                    'updated_at' => $translation->updated_at ? $translation->updated_at->toIso8601String() : null,
                ];
                return $result;
            } catch (\Exception $e) {
                \Log::error('Error mapping translation', [
                    'translation_id' => $translation->id,
                    'error' => $e->getMessage()
                ]);
                return null;
            }
        })->filter(); // Remove any null entries

        \Log::info('Returning translations:', ['count' => $response->count()]);

        return response()->json($response->values()->all());
    } catch (\Exception $e) {
        \Log::error('Error in show method:', [
            'message' => $e->getMessage(),
            'file' => $e->getFile(),
            'line' => $e->getLine(),
            'trace' => $e->getTraceAsString()
        ]);
        return response()->json([
            'error' => 'Internal server error', 
            'message' => $e->getMessage()
        ], 500);
    }
}

    

    /**
     * Display the specified resource (single translation by ID).
     */
    public function show(string $id)
{
    try {
        $user = Auth::guard('api')->user();
        
        if (!$user) {
            return response()->json(['error' => 'Unauthorized'], 401);
        }

        $translation = Translation::with(['translatedText', 'translatedAudio'])
                        ->where('id', $id)
                        ->where('user_id', $user->id)
                        ->first();

        if (!$translation) {
            return response()->json(['error' => 'Translation not found'], 404);
        }

        return response()->json([
            'id' => $translation->id,
            'input_type' => $translation->input_type,
            'input_data' => $translation->input_data,
            'translated_text' => $translation->translatedText ? $translation->translatedText->text : '',
            'translated_audio' => $translation->translatedAudio ? $translation->translatedAudio->audio_path : null,
            'created_at' => $translation->created_at ? $translation->created_at->toIso8601String() : null,
            'updated_at' => $translation->updated_at ? $translation->updated_at->toIso8601String() : null,
        ]);
    } catch (\Exception $e) {
        \Log::error('Error in show method:', ['error' => $e->getMessage()]);
        return response()->json(['error' => 'Internal server error'], 500);
    }
}

    /**
     * Update the specified resource in storage.
     */
    public function update(Request $request, string $id)
    {
        $user = Auth::guard('api')->user();
        
        if (!$user) {
            return response()->json(['error' => 'Unauthorized'], 401);
        }
        
        $translation = Translation::with(['translatedText', 'translatedAudio'])
                        ->where('id', $id)
                        ->where('user_id', $user->id)
                        ->first();
    
        if (!$translation) {
            return response()->json(['message' => 'Translation not found'], 404);
        }
    
        // Validate the incoming request data
        // Testing mode: Very high limit (1000MB = 1000000 KB) to allow large video files
        $validatedData = $request->validate([
            'input_type' => 'sometimes|in:video,image,live',
            'input_data' => 'sometimes|nullable|file|mimes:mp4,jpg,jpeg,png|max:1000000',
            'translated_text' => 'sometimes|string',
            'translated_audio' => 'sometimes|file|mimes:mp3,wav',
        ]);
    
        // Update the translation
        if ($request->hasFile('input_data')) {
            $inputDataPath = $request->file('input_data')->store('uploads/input_data', 'public');
            $translation->input_data = $inputDataPath;
        }
    
        $translation->update($validatedData);
    
        // Update the translated text
        if ($request->filled('translated_text')) {
            if ($translation->translatedText) {
                $translation->translatedText->update([
                    'text' => $validatedData['translated_text'],
                ]);
            } else {
                $translation->translatedText()->create([
                    'text' => $validatedData['translated_text'],
                ]);
            }
        }
    
        // Update the translated audio (if present)
        if ($request->hasFile('translated_audio')) {
            $translatedAudioPath = $request->file('translated_audio')->store('uploads/translated_audio', 'public');
            // Check if audio already exists, update it; otherwise create it
            if ($translation->translatedAudio) {
                $translation->translatedAudio->update([
                    'audio_path' => $translatedAudioPath,
                ]);
            } else {
                $translation->translatedAudio()->create([
                    'audio_path' => $translatedAudioPath,
                ]);
            }
        }
    
        // Reload the translation with relationships
        $translation->load(['translatedText', 'translatedAudio']);
        
        return response()->json([
            'id' => $translation->id,
            'input_type' => $translation->input_type,
            'input_data' => $translation->input_data,
            'translated_text' => $translation->translatedText ? $translation->translatedText->text : '',
            'translated_audio' => $translation->translatedAudio ? $translation->translatedAudio->audio_path : null,
            'created_at' => $translation->created_at ? $translation->created_at->toIso8601String() : null,
            'updated_at' => $translation->updated_at ? $translation->updated_at->toIso8601String() : null,
        ]);
    }
    
    /**
     * Remove the specified resource from storage.
     */
    public function destroy(string $id)
    {
        // Find the translation by ID
        $translation = Translation::find($id);

        if (!$translation) {
            return response()->json(['message' => 'Translation not found'], 404);
        }

        // Delete the translation
        $translation->delete();

        return response()->json(['message' => 'Translation deleted successfully']);

    }
}
