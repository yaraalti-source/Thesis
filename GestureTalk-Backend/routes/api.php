<?php

use App\Http\Controllers\AuthController;
use App\Http\Controllers\SpeechController;
use App\Http\Controllers\TranslationController;
use App\Http\Controllers\UserController;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Route;

Route::controller(AuthController::class)->group(function () {
    Route::post('login', 'login');
    Route::post('register', 'register');
    Route::post('logout', 'logout');
    Route::post('refresh', 'refresh');
});

Route::resource('users', UserController::class);

Route::put('/updateUser', [UserController::class, 'update']);
Route::post('/upload-image', [UserController::class, 'uploadImage']);
Route::post('/speech', [SpeechController::class, 'generateSpeech']);
Route::middleware('auth:api')->get('getUser', [UserController::class, 'show']);
// Get all translations for authenticated user
Route::middleware('auth:api')->get('/get-translations',[TranslationController::class,'getUserTranslations']);
Route::middleware('auth:api')->resource('translations',TranslationController::class);
Route::middleware('authenticate')->get('/verify-token', function (Request $request) {
    $user = Auth::user();
    
    if ($user) {
        return response()->json(['valid' => true]);
    } else {
        return response()->json(['valid' => false], 401);
    }
});