<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class Translation extends Model
{
    use HasFactory;
    protected $fillable=[
        'user_id',
        'translated_text',
        'input_type',
        'input_data',
        'translated_audio',
    ];
    public function user()
    {
        return $this->belongsTo(User::class);
    }
    public function translatedText()
{
    return $this->hasOne(TranslatedText::class);
}

public function translatedAudio()
{
    return $this->hasOne(TranslatedAudio::class);
}


}
