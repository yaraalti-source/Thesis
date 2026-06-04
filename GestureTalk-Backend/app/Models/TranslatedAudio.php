<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class TranslatedAudio extends Model
{
    use HasFactory;

    protected $fillable = [
        'translation_id', // Foreign key to the translations table
        'audio_path', // Path to the audio file
    ];

    /**
     * Define the relationship to the Translation model.
     * Each TranslatedAudio belongs to one Translation.
     */
    public function translation()
    {
        return $this->belongsTo(Translation::class);
    }
}
