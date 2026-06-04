<?php

namespace Database\Factories;

use App\Models\Translation;
use Illuminate\Database\Eloquent\Factories\Factory;

/**
 * @extends \Illuminate\Database\Eloquent\Factories\Factory<\App\Models\TranslatedAudio>
 */
class TranslatedAudioFactory extends Factory
{
    /**
     * Define the model's default state.
     *
     * @return array<string, mixed>
     */
    public function definition(): array
    {
        return [
            'translation_id' => Translation::factory(), 
            'audio_path' => 'uploads/translated_audio/' . $this->faker->lexify('??????.mp3'), 
            'created_at' => now(),
            'updated_at' => now(),
        ];
    }
}
