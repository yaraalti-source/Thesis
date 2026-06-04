<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class TranslatedText extends Model
{
    use HasFactory;

    protected $fillable = [
        'translation_id', // Foreign key to the translations table
        'text',
    ];

    /**
     * Define the relationship to the Translation model.
     * Each TranslatedText belongs to one Translation.
     */
    public function translation()
    {
        return $this->belongsTo(Translation::class);
    }
}
