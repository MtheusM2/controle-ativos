import { useState } from 'react';
import {
  Save,
  X,
  Upload,
  FileText,
  Calendar,
  MapPin,
  DollarSign,
  Tag,
  Package
} from 'lucide-react';

interface AssetFormProps {
  assetId?: string;
  onSave: () => void;
  onCancel: () => void;
}

export function AssetForm({ assetId, onSave, onCancel }: AssetFormProps) {
  const [formData, setFormData] = useState({
    name: assetId ? 'Monitor Dell UltraSharp 27"' : '',
    category: assetId ? 'Informática' : '',
    serialNumber: assetId ? 'DELL2023001' : '',
    status: assetId ? 'active' : '',
    location: assetId ? 'Sala 301' : '',
    purchaseDate: assetId ? '2023-01-15' : '',
    value: assetId ? '2500.00' : '',
    description: assetId ? 'Monitor profissional de 27 polegadas com resolução 4K' : '',
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave();
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  return (
    <div className="max-w-4xl mx-auto">
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Header */}
        <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-gray-900">{assetId ? 'Editar Ativo' : 'Novo Ativo'}</h2>
              <p className="text-sm text-gray-500 mt-1">
                {assetId ? 'Atualize as informações do ativo' : 'Preencha os dados para cadastrar um novo ativo'}
              </p>
            </div>
            <button
              type="button"
              onClick={onCancel}
              className="p-2 text-gray-400 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Basic Info */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="md:col-span-2">
              <label htmlFor="name" className="block text-sm text-gray-700 mb-2">
                <div className="flex items-center gap-2">
                  <Package className="w-4 h-4" />
                  Nome do Ativo *
                </div>
              </label>
              <input
                id="name"
                name="name"
                type="text"
                value={formData.name}
                onChange={handleChange}
                placeholder="Ex: Monitor Dell UltraSharp 27 polegadas"
                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary outline-none"
                required
              />
            </div>

            <div>
              <label htmlFor="category" className="block text-sm text-gray-700 mb-2">
                <div className="flex items-center gap-2">
                  <Tag className="w-4 h-4" />
                  Categoria *
                </div>
              </label>
              <select
                id="category"
                name="category"
                value={formData.category}
                onChange={handleChange}
                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary outline-none"
                required
              >
                <option value="">Selecione...</option>
                <option value="Informática">Informática</option>
                <option value="Mobiliário">Mobiliário</option>
                <option value="Audiovisual">Audiovisual</option>
                <option value="Veículos">Veículos</option>
                <option value="Outros">Outros</option>
              </select>
            </div>

            <div>
              <label htmlFor="serialNumber" className="block text-sm text-gray-700 mb-2">
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4" />
                  Número de Série *
                </div>
              </label>
              <input
                id="serialNumber"
                name="serialNumber"
                type="text"
                value={formData.serialNumber}
                onChange={handleChange}
                placeholder="Ex: DELL2023001"
                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary outline-none font-mono"
                required
              />
            </div>

            <div>
              <label htmlFor="status" className="block text-sm text-gray-700 mb-2">
                Status *
              </label>
              <select
                id="status"
                name="status"
                value={formData.status}
                onChange={handleChange}
                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary outline-none"
                required
              >
                <option value="">Selecione...</option>
                <option value="active">Ativo</option>
                <option value="maintenance">Em Manutenção</option>
                <option value="inactive">Inativo</option>
              </select>
            </div>

            <div>
              <label htmlFor="location" className="block text-sm text-gray-700 mb-2">
                <div className="flex items-center gap-2">
                  <MapPin className="w-4 h-4" />
                  Localização *
                </div>
              </label>
              <input
                id="location"
                name="location"
                type="text"
                value={formData.location}
                onChange={handleChange}
                placeholder="Ex: Sala 301"
                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary outline-none"
                required
              />
            </div>

            <div>
              <label htmlFor="purchaseDate" className="block text-sm text-gray-700 mb-2">
                <div className="flex items-center gap-2">
                  <Calendar className="w-4 h-4" />
                  Data de Compra *
                </div>
              </label>
              <input
                id="purchaseDate"
                name="purchaseDate"
                type="date"
                value={formData.purchaseDate}
                onChange={handleChange}
                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary outline-none"
                required
              />
            </div>

            <div>
              <label htmlFor="value" className="block text-sm text-gray-700 mb-2">
                <div className="flex items-center gap-2">
                  <DollarSign className="w-4 h-4" />
                  Valor (R$) *
                </div>
              </label>
              <input
                id="value"
                name="value"
                type="number"
                step="0.01"
                value={formData.value}
                onChange={handleChange}
                placeholder="0,00"
                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary outline-none"
                required
              />
            </div>

            <div className="md:col-span-2">
              <label htmlFor="description" className="block text-sm text-gray-700 mb-2">
                Descrição
              </label>
              <textarea
                id="description"
                name="description"
                value={formData.description}
                onChange={handleChange}
                rows={3}
                placeholder="Informações adicionais sobre o ativo..."
                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary outline-none resize-none"
              />
            </div>
          </div>
        </div>

        {/* Attachments */}
        <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
          <h3 className="text-gray-900 mb-4">Anexos</h3>

          <div className="space-y-4">
            {/* Upload Area */}
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-primary transition-colors cursor-pointer">
              <Upload className="w-10 h-10 text-gray-400 mx-auto mb-3" />
              <p className="text-sm text-gray-600 mb-1">
                Clique para fazer upload ou arraste os arquivos
              </p>
              <p className="text-xs text-gray-500">
                Nota fiscal, garantia, fotos do ativo (PDF, JPG, PNG - máx 10MB)
              </p>
            </div>

            {/* Existing Files */}
            {assetId && (
              <div className="space-y-2">
                <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-200">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-red-100 rounded-lg">
                      <FileText className="w-4 h-4 text-primary" />
                    </div>
                    <div>
                      <p className="text-sm text-gray-900">nota_fiscal_2023_001.pdf</p>
                      <p className="text-xs text-gray-500">2.5 MB • 15/01/2023</p>
                    </div>
                  </div>
                  <button type="button" className="text-red-600 hover:bg-red-50 p-2 rounded-lg transition-colors">
                    <X className="w-4 h-4" />
                  </button>
                </div>

                <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-200">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-red-100 rounded-lg">
                      <FileText className="w-4 h-4 text-primary" />
                    </div>
                    <div>
                      <p className="text-sm text-gray-900">garantia_dell_monitor.pdf</p>
                      <p className="text-xs text-gray-500">1.8 MB • 15/01/2023</p>
                    </div>
                  </div>
                  <button type="button" className="text-red-600 hover:bg-red-50 p-2 rounded-lg transition-colors">
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-4">
          <button
            type="button"
            onClick={onCancel}
            className="px-6 py-2.5 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Cancelar
          </button>
          <button
            type="submit"
            className="flex items-center gap-2 px-6 py-2.5 bg-primary text-white rounded-lg hover:bg-red-700 transition-colors shadow-md hover:shadow-lg"
          >
            <Save className="w-4 h-4" />
            <span>{assetId ? 'Salvar Alterações' : 'Cadastrar Ativo'}</span>
          </button>
        </div>
      </form>
    </div>
  );
}
